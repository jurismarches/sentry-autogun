# ~*~ coding: utf-8 ~*~
import re

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from redmine import Redmine
from sentry.plugins.bases.notify import NotificationPlugin


class RedmineOptionsForm(forms.Form):
    host = forms.URLField(
        label="Redmine host",
        help_text=_("e.g. http://bugs.redmine.org"))
    key = forms.CharField(
        label="Redmine user API Key",
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=False)
    username = forms.CharField(
        label="Redmine username",
        widget=forms.TextInput(attrs={'class': 'span9'}),
        help_text=_("Use username/password only if you can't use API key or if you have an http auth."),
        required=False)
    password = forms.CharField(
        label="Redmine password",
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=False)
    project = forms.CharField(
        label="Redmine project",
        help_text=_("example: scripts"),
        widget=forms.TextInput(attrs={'class': 'span9'}))
    tracker = forms.CharField(
        label="Redmine tracker ID",
        widget=forms.TextInput(attrs={'class': 'span9'}))
    ignored_exceptions = forms.CharField(
        label="Ignored exceptions separate by commat as Python regexp. Theses matched exceptions won't be created in Redmine.",
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=False)
    same_issues = forms.CharField(
        label="When matched on Redmine issues, plugin will just add a comment and not create a new issue.",
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=False)
    round_robin = forms.BooleanField(
        label="Round robin",
        widget=forms.CheckboxInput(),
        help_text="Round robin for assigned_to field in Redmine. Example: 2,3,4",
        required=False)
    round_robin_ids = forms.CharField(
        label="Round robin users ids",
        widget=forms.TextInput(attrs={'class': 'span9'}),
        required=False)

    def clean(self):
        config = self.cleaned_data
        if not all(config.get(k) for k in ('host', 'project', 'tracker')):
            raise forms.ValidationError('Missing required configuration value')
        if not config.get('key') or not config.get('username') and config.get('password'):
            raise forms.ValidationError('Need at least username, password or just API key')
        if len(config.get('key')) < 40:
            raise forms.ValidationError('Redmine API key is malformed')
        if config.get('round_robin') and not config.get('round_robin_ids'):
            raise forms.ValidationError('Need round robin users ids if round robin is activated')
        return config


class AutogunPlugin(NotificationPlugin):
    author = 'Geoffrey Lehée'
    version = '0.1.5'
    description = "Integrate Redmine issue tracking by linking a user account to a project."
    slug = 'autogun-redmine'
    title = _('Redmine Autogun')
    conf_title = 'Redmine Autogun'
    conf_key = 'redmine-autogun'
    project_conf_form = RedmineOptionsForm

    def is_configured(self, project, **kwargs):
        return all(self.get_option(k, project) for k in ('host', 'project', 'tracker'))

    def post_process(self, group, event, is_new, is_sample, **kwargs):
        if not is_new or not self.is_configured(event.project):
            return

        event_url = "%s/%s/%s/group/%s/" % (
            settings.SENTRY_URL_PREFIX,
            event.team.slug,
            event.project.slug,
            event.group.id)
        content = event.as_dict()['extra']['message']
        message = '"Sentry event url":%s\n\n<pre>\n%s\n</pre>\n' % (event_url, content)

        self.send_notification(event.project, message, event.error(), event.as_dict(), event_url)

    def send_notification(self, project, message, error, info_dict, event_url):
        msg = info_dict['sentry.interfaces.Message']['message']

        if self.get_option('ignored_exceptions', project).strip():
            for exception in self.get_option('ignored_exceptions', project).split(','):
                _r = re.compile(exception, re.IGNORECASE)
                if _r.search(msg):
                    return

        redmine = Redmine(
            self.get_option('host', project),
            username=self.get_option('username', project) or "",
            password=self.get_option('password', project) or "",
            key=self.get_option('key', project) or "",
            version=2.1)

        ################################################################################
        # Specific jurismarches
        ################################################################################
        spider = dict(info_dict.get('tags', [])).get('spider')
        site_id = None
        argv = info_dict.get('extra', {}).get('sys.argv', [])
        if argv:
            for arg in argv:
                if arg.startswith('id='):
                    site_id = arg.split('=')[-1]
                    break

        extra_fields = [
            {'id': '2', 'value': '17'}
        ]

        if spider:
            extra_fields.append({'id': '1', 'value': spider})

        if site_id:
            extra_fields.append({'id': '10', 'value': site_id})
        ################################################################################

        subject = (msg[:80] + '..') if len(msg) > 80 else msg

        try:
            redmine_project = redmine.projects[self.get_option('project', project)]

            # Looking for related issues already open
            already_open = False
            if self.get_option('same_issues', project).strip():
                for issue in redmine_project.issues(cf_1=spider, status_id="open"):
                    for pattern in self.get_option('same_issues', project).split(','):
                        _r = re.compile(pattern, re.IGNORECASE)
                        if _r.search(issue.subject):
                            issue.save('Related event: %s' % event_url)
                            already_open = True
                        else:
                            issue.save('*New event*\n\n%s' % message)
                            already_open = True
                        if already_open:
                            return

            issue_data = {
                'subject': subject,
                'tracker_id': self.get_option('tracker', project),
                'description': message,
                'custom_fields': extra_fields  # Specific jurismarches custom_fields
            }

            if self.get_option('round_robin', project):
                round_robin_ids = [int(idx) for idx in self.get_option('round_robin_ids', project).split(',')]

                # Get next user using round Robin
                if round_robin_ids:
                    round_robin = redmine_project.issues(status_id='*', sort='created_on:desc', limit='1', assigned_to_id='*')
                    if round_robin:
                        last_user = list(round_robin)[0].assigned_to
                        if last_user:
                            try:
                                next_user_index = round_robin_ids.index(last_user.id) + 1
                                if next_user_index >= len(round_robin_ids):
                                    next_user_index = 0
                            except Exception:
                                next_user_index = 0
                        else:
                            next_user_index = 0

                        issue_data.update({
                            'assigned_to': round_robin_ids[next_user_index]
                        })

            redmine_project.issues.new(**issue_data)
        except Exception as err:
            raise err


# Backwards-compatibility
NotifyConfigurationForm = RedmineOptionsForm
NotifyPlugin = AutogunPlugin

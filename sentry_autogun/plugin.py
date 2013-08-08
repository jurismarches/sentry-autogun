# ~*~ coding: utf-8 ~*~
import re
from urllib2 import HTTPError
from redmine import Redmine
from django import forms
from django.utils.translation import ugettext_lazy as _
from sentry.plugins.bases.notify import NotificationPlugin
from django.conf import settings

class RedmineOptionsForm(forms.Form):
    host = forms.URLField(label="Redmine host", help_text=_("e.g. http://bugs.redmine.org"))
    key = forms.CharField(label="Redmine user API Key", widget=forms.TextInput(attrs={'class': 'span9'}), required=False)
    username = forms.CharField(label="Redmine username", widget=forms.TextInput(attrs={'class': 'span9'}), required=False)
    password = forms.CharField(label="Redmine password", widget=forms.TextInput(attrs={'class': 'span9'}), required=False)
    project = forms.CharField(label="Redmine project", help_text=_("example: scripts"), widget=forms.TextInput(attrs={'class': 'span9'}))
    tracker = forms.CharField(label="Redmine tracker ID", widget=forms.TextInput(attrs={'class': 'span9'}))
    ignored_exceptions = forms.CharField(
                            label="Ignored exceptions separate by commat.",
                            widget=forms.TextInput(attrs={'class': 'span9'}),
                            help_text=_("Examples: IndexError,HttpError,attributError,ioERROR"),
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
    version = '0.1.1'
    description = "Integrate Redmine issue tracking by linking a user account to a project."
    slug = 'autogun-redmine'
    title = _('Redmine Autogun')
    conf_title = 'Redmine Autogun'
    conf_key = 'redmine-autogun'
    project_conf_form = RedmineOptionsForm

    def is_configured(self, project, **kwargs):
        return all(self.get_option(k, project) for k in
                    ('host', 'project', 'tracker'))

    def post_process(self, group, event, is_new, is_sample, **kwargs):
        if not is_new or not self.is_configured(event.project):
            return

        message = """
"Sentry event url":%s/%s/%s/group/%s/

<pre>
%s
</pre>
""" % (settings.SENTRY_URL_PREFIX, event.team.slug, event.project.slug, event.group.id, event.as_dict()['extra']['message'])

        self.send_notification(event.project, message, event.error(), event.as_dict())

    def send_notification(self, project, message, error, info_dict):
        msg = info_dict['sentry.interfaces.Message']['message']
        for exception in self.get_option('ignored_exceptions', project).split(','):
            _r = re.compile(exception, re.IGNORECASE)
            if _r.match(msg):
                return

        redmine = Redmine(
                    self.get_option('host', project),
                    username=self.get_option('username', project) or "",
                    password=self.get_option('password', project) or "",
                    key=self.get_option('key', project) or "",
                    version=2.1)

        # Specific jurismarches
        spider = [tag for tag in info_dict.get('tags') if tag[0] == 'spider'][0][1]
        extra_fields =  [
                            {'id': '1', 'value': spider},
                            {'id': '2', 'value': '17'}
        ]

        subject = (msg[:80] + '..') if len(msg) > 80 else msg

        try:
            redmine_project = redmine.projects[self.get_option('project', project)]

            issue_data = {
                'subject': subject,
                'tracker_id': self.get_option('tracker', project),
                'description': message,
                'custom_fields': extra_fields
            }

            if self.get_option('round_robin', project):
                round_robin_ids = [int(idx) for idx in self.get_option('round_robin_ids', project).split(',')]
                print(round_robin_ids)

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

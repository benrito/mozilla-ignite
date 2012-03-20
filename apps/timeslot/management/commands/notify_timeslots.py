from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.template import Context
from challenges.models import Submission, Phase
from timeslot.models import TimeSlot, Release

if 'django_mailer' in settings.INSTALLED_APPS:
    from django_mailer import send_mail
else:
    from django.core.mail import send_mail



class Command(BaseCommand):
    help = """Notifies the green lit teams when they are ready to book"""

    def handle(self, *args, **options):
        site = Site.objects.get_current()
        release = Release.objects.get_current()
        if not release:
            raise CommandError('There is not an active Release')
        answer = raw_input("This will remind INMEDIATELY the green-lit teams "
                           "that haven't book a timeslot for the '%s' release."
                           " Proceed? (yes/no)? " % release)
        if answer != 'yes':
            raise CommandError('Phew. Submission canceled.')
        booked_qs = release.timeslot_set.select_related('submission').\
            filter(is_booked=True)
        booked_ids = [i.submission.id for i in booked_qs]
        args = [release.phase]
        if release.phase_round:
            args.append(release.phase_round)
        submission_list = Submission.objects.green_lit(*args).\
            select_related('created_by', 'create_by__user').\
            filter(~Q(id__in=booked_ids))
        email_template = lambda x: 'timeslot/email/reminder/%s.txt' % x
        for i, submission in enumerate(submission_list, start=1):
            profile = submission.created_by
            if not profile.user.email:
                continue
            context = Context({
                'submission': submission,
                'profile': profile,
                'site': site,
                })
            subject = render_to_string(email_template('subject'),
                                       context)
            subject = subject.splitlines()[0]
            body = render_to_string(email_template('body'),
                                    context)
            recipient = '%s <%s>' % (profile.name, profile.user.email)
            print 'Emailing %s: %s' % (recipient, submission)
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,
                      [recipient, ], fail_silently=False)
        print 'Emailed %s recipients' % i

from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.syndication.views import feed

from notification.models import *
from notification.decorators import basic_auth_required, simple_basic_auth_callback
from notification.feeds import NoticeUserFeed

@basic_auth_required(realm='Notices Feed', callback_func=simple_basic_auth_callback)
def feed_for_user(request):
    url = "feed/%s" % request.user.username
    return feed(request, url, {
        "feed": NoticeUserFeed,
    })

@login_required
def notices(request, template="notification/notices.html", extra_context=None):
    extra_context = extra_context or {}
    notice_types = NoticeType.objects.all()
    notices = Notice.objects.notices_for(request.user, on_site=True)
    settings_table = []
    for notice_type in NoticeType.objects.all():
        settings_row = []
        for medium_id, medium_display in NOTICE_MEDIA:
            form_label = "%s_%s" % (notice_type.label, medium_id)
            setting = get_notification_setting(request.user, notice_type, medium_id)
            if request.method == "POST":
                if request.POST.get(form_label) == "on":
                    setting.send = True
                else:
                    setting.send = False
                setting.save()
            settings_row.append((form_label, setting.send))
        settings_table.append({"notice_type": notice_type, "cells": settings_row})

    notice_settings = {
        "column_headers": [medium_display for medium_id, medium_display in NOTICE_MEDIA],
        "rows": settings_table,
    }

    context = {
        "notices": notices,
        "notice_types": notice_types,
        "notice_settings": notice_settings,
    }
    for key, value in extra_context.items():
        if callable(value):
            context[key] = value()
        else:
            context[key] = value

    return render_to_response(template, context,
                              context_instance=RequestContext(request))

@login_required
def single(request, id, template="notification/single.html"):
    notice = get_object_or_404(Notice, id=id)
    if request.user == notice.user:
        return render_to_response(template, {
            "notice": notice,
        }, context_instance=RequestContext(request))
    raise Http404

@login_required
def archive(request, noticeid=None, next_page=None):
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
        except Notice.DoesNotExist:
            pass
        else:
            # you can archive other users' notices
            # only if you are superuser.
            if request.user == notice.user or request.user.is_superuser:
                notice.archive()
    return redirect(next_page)

@login_required
def delete(request, noticeid=None, next_page=None):
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.user or request.user.is_superuser:
                notice.delete()
            else:   # you can delete other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)

@login_required
def mark_all_seen(request):
    for notice in Notice.objects.notices_for(request.user, unseen=True):
        notice.unseen = False
        notice.save()
    return HttpResponseRedirect(reverse("notification_notices"))


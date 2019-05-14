#!/usr/bin/env python3

# Script to PRs in QA
# Usage: run from root directory of this project as:
#   ./scripts/dev_tools_scripts/get_prs_in_qa
# It will give you the list of PRs since the last Release and their status: Checked or Not

# Docs:
# - python-slackclient: https://github.com/slackapi/python-slackclient

__author__ = 'gabriel blondeau - gabriel@builton.dev'

__version__ = "0.1"

import requests
import os
import re
import slack

from github import Github, PullRequest
from termcolor import cprint

GIT_HUB_TOKEN = os.environ['GIT_HUB_TOKEN']

slack_client = slack.WebClient(token=os.environ['SLACK_API_TOKEN'])

# settings
TERMINATOR = "--------------------------------\n"

# Marks
TESTED_APPROVED = "Tested and Approved"
NOT_TESTED = "not tested"
TESTED_FAILED = "Tested and Failed"

marks = {
    TESTED_APPROVED: ":heavy_check_mark:",
    NOT_TESTED: ":white_check_mark:",
    TESTED_FAILED: ":heavy_multiplication_x:"
}


def run_script(request):
    request_json = request.get_json()
    slack_channel = request_json.get('channel', '#back')

    prs, previous_version = get_data()
    ordered_prs = organize_by_status(prs)
    text = generate_text(ordered_prs, previous_version)
    post_msg_slack(text, slack_channel)


def get_data():
    cprint("-> accessing github's data...", 'green')
    g = Github(GIT_HUB_TOKEN)

    cprint("    finding repo...")
    backend = g.get_repo(os.environ['REPOSITORY'])

    cprint("    getting prs...")
    pulls = backend.get_pulls(state='closed', sort='updated', direction='desc')

    prs = []

    def find_last_version(pulls):
        for pull in pulls:
            if re.match(r'^v\.?[0-9]+\.[0-9]+\.[0-9]+$', pull.title):
                return pull.title
            cprint("    " + pull.title, 'cyan')
            prs.append(pull)

    previous_version = find_last_version(pulls)
    cprint('-> DONE! found %s prs since last release =)' % len(prs), 'green')
    return prs, previous_version


def organize_by_status(prs=[]):
    tested_approved = []
    not_tested = []
    test_failed = []

    for pr in prs:
        labels = pr.get_labels()
        organized = False

        if labels.totalCount == 0:
            not_tested.append(pr)
            continue

        while not organized:
            for label in labels:
                if TESTED_APPROVED == label.name:
                    tested_approved.append(pr)
                    organized = True
                elif TESTED_FAILED == label.name:
                    test_failed.append(pr)
                    organized = True

            if not organized:
                not_tested.append(pr)
                organized = True

    return {TESTED_APPROVED: tested_approved, NOT_TESTED: not_tested, TESTED_FAILED: test_failed}


def generate_text(prs_by_status={}, previous_version=""):
    text = """From the Last Release: %s\n""" % previous_version
    text += "Prs in QA: \n"
    cprint("Prs in QA:", 'green')
    for kind, prs in prs_by_status.items():
        if len(prs) == 0:
            continue

        for pr in prs:
            msg = "-[%s] %s: %s" % (marks[kind], pr.title, get_short_link(pr))
            text += msg + "\n"
            cprint(msg, "yellow")
        text += TERMINATOR
        cprint(TERMINATOR)

    text += "[%s] In QA, need to be tested \n" \
            "[%s] In QA, Tested and ready to be in the next release \n" \
            "[%s] In QA, Tested but doesn't work as purposed" \
            % (marks[NOT_TESTED], marks[TESTED_APPROVED], marks[TESTED_FAILED])

    cprint("[%s] In QA, need to be tested" % marks[NOT_TESTED])
    cprint("[%s] In QA, Tested and ready to be in the next release" % marks[TESTED_APPROVED])
    cprint("[%s] In QA, Tested but doesn't work as purposed" % marks[TESTED_FAILED])

    return text


def get_short_link(pr: PullRequest):
    return "<%s|#%s>" % (pr.html_url, pr.number)


def post_msg_slack(text, channel):
    slack_client.chat_postMessage(channel=channel, text=text)

# TODO: Raise it after each Merge PR into DEV
# TODO: Raise it after Label is Updated
# TODO: Instead of Write new Message every time, edit the previous one (add a title: vX.X.X)
from jira import Issue

from dailybot.constants import (DAILY_MODAL_SUBMISSION, ACTIONS_ISSUE_DAILY_FORM, ISSUE_LINK_ACTION,
                                ISSUE_SUMMERY_ACTION, GENERAL_COMMENTS_ACTION, BULK_ID_FORMAT, SAVE_USER_CONFIGURATIONS,
                                SELECT_USER_TEAM, SELECT_USER_BOARD, JIRA_EMAIL_ACTION, JIRA_API_TOKEN_ACTION,
                                JIRA_SERVER_ACTION, JiraHostType, JIRA_HOST_TYPE, MAX_LEN_SLACK_SELECTOR,
                                TYPE_USER_BOARD, TYPE_OR_SELECT_USER_BOARD, SAVE_USER_BOARD, IGNORE_ISSUE_IN_DAILY_FORM,
                                SELECT_STATUS_ISSUE_DAILY_FORM, OPEN_IN_JIRA, ADD_TEAM)
from dailybot.jira_utils import get_jira_projects, get_optional_statuses
from dailybot.mongodb import Team, User, SlackUserData, Daily, DailyIssueReport

from .models import *


def issue_report_component_blocks(user: User, issue: Issue, issue_reports: List[DailyIssueReport]) -> List[Block]:
    issue_report = None
    for report in issue_reports:
        if report.key == issue.key:
            issue_report = report

    status = issue.get_field('status')
    initial_option = Option(text=Text(type=TextType.PlainText, text=status.name), value=status.name)

    return [
        HeaderBlock(text=Text(type=TextType.PlainText, text=f'{issue.key}: {issue.get_field("summary")}')),
        ActionsBlock(
            block_id=BULK_ID_FORMAT.format(key=issue.key, action=ACTIONS_ISSUE_DAILY_FORM),
            elements=[
                Selector(
                    type=BlockElementType.Checkboxes,
                    action_id=IGNORE_ISSUE_IN_DAILY_FORM,
                    options=[
                        Option(
                            text=Text(type=TextType.MarkdownText, text="Ignore this issue"),
                            value="ignore-issue"
                        )
                    ]
                ),
                SelectMenu(
                    type=BlockElementType.StaticSelect,
                    action_id=SELECT_STATUS_ISSUE_DAILY_FORM,
                    placeholder=Text(type=TextType.PlainText, text="Select current status"),
                    initial_option=initial_option,
                    options=[initial_option, *(
                        Option(text=Text(type=TextType.PlainText, text=s), value=s)
                        for s in get_optional_statuses(user=user, issue_key=issue.key) if s != status.name
                    )]
                ),
                Button(
                    type=BlockElementType.Button,
                    action_id=ISSUE_LINK_ACTION,
                    text=Text(type=TextType.PlainText, text="Open in Jira"),
                    value=f"link-issue-{issue.key}",
                    url=issue.permalink()
                )
            ]
        ),
        InputBlock(
            block_id=BULK_ID_FORMAT.format(key=issue.key, action=ISSUE_SUMMERY_ACTION),
            optional=True,
            label=Text(type=TextType.PlainText, text="Progress details"),
            element=Input(
                type=BlockElementType.PlainTextInput,
                action_id=ISSUE_SUMMERY_ACTION
            )
        ),
        *(
            [ContextBlock(elements=[Text(type=TextType.PlainText, text=f"Stored data: {issue_report.details}")])]
            if issue_report and issue_report.details else []
        ),
        DividerBlock()
    ]


def generate_daily_modal(user: User, issues: List[Issue], daily: Daily):
    reports = daily.reports.get(user.slack_data.user_id)
    issue_reports = reports.issue_reports if reports else []
    issue_report_components = [
        component
        for issue in issues for component in issue_report_component_blocks(user, issue, issue_reports)
    ]
    # TODO: move modal to base element
    return {
        "type": "modal",
        "callback_id": DAILY_MODAL_SUBMISSION,
        "submit": Text(type=TextType.PlainText, text="Submit").dict(exclude_none=True, by_alias=True),
        "close": Text(type=TextType.PlainText, text="Cancel").dict(exclude_none=True, by_alias=True),
        "title": Text(type=TextType.PlainText, text="Daily Report").dict(exclude_none=True, by_alias=True),
        "blocks": serialize_blocks([
            SectionBlock(text=Text(
                type=TextType.MarkdownText,
                text=(
                    f"*Hi <@{user.slack_data.user_id}>!* Please change the statuses of the following issues to the "
                    f"updated status, and add comments of the progress of the issues. if you re-fill this form, copy "
                    "the stored data to the input box"
                )
            )),
            *issue_report_components,
            InputBlock(
                block_id=GENERAL_COMMENTS_ACTION,
                optional=True,
                element=Input(type=BlockElementType.PlainTextInput, multiline=True, action_id=GENERAL_COMMENTS_ACTION),
                label=Text(type=TextType.PlainText, text="Other comments / blockers")
            ),
            *(
                [ContextBlock(
                    elements=[Text(type=TextType.PlainText, text=f"Stored data: {reports.general_comments}")]
                )] if reports and reports.general_comments else []
            ),
        ])
    }


def generate_home_tab_view(teams: List[Team]):
    return {
        "type": "home",
        "blocks": serialize_blocks([
            SectionBlock(text=Text(type=TextType.MarkdownText, text="*Hey there! im DailyBot :smile:*")),
            DividerBlock(),
            SectionBlock(text=Text(
                type=TextType.MarkdownText,
                text=("I was created by <@U020JKP23SR|Tugy> to bring happiness to the agile wor ld by skipping dailys "
                      "and not wasting time each day, and just move this dailys into writing.")
            )),
            SectionBlock(text=Text(type=TextType.MarkdownText, text="Lets configure your profile :gear:")),
            DividerBlock(),
            InputBlock(
                block_id=JIRA_SERVER_ACTION,
                label=Text(type=TextType.PlainText, text="Jira server url"),
                hint=Text(type=TextType.PlainText,
                    text="https://<your-domain>.atlassian.net/ (if using cloud)  *<!> Dont forget the 'https://'*",
                    emoji=False
                ),
                element=Input(type=BlockElementType.PlainTextInput, action_id=JIRA_SERVER_ACTION),
            ),
            InputBlock(
                block_id=JIRA_HOST_TYPE,
                label=Text(type=TextType.PlainText, text="Select your Jira host type"),
                element=SelectElement(
                    type=BlockElementType.StaticSelect,
                    action_id=JIRA_HOST_TYPE,
                    placeholder=Text(type=TextType.PlainText, text="Select options"),
                    initial_option=Option(
                        text=Text(type=TextType.PlainText, text=JiraHostType.Cloud.name),
                        value=JiraHostType.Cloud.name
                    ),
                    options=[
                        Option(
                            text=Text(type=TextType.PlainText, text=JiraHostType.Cloud.name),
                            value=JiraHostType.Cloud.name
                        ),
                        Option(
                            text=Text(type=TextType.PlainText, text=JiraHostType.Local.name),
                            value=JiraHostType.Local.name
                        ),
                    ]
                )
            ),
            InputBlock(
                block_id=JIRA_EMAIL_ACTION,
                label=Text(type=TextType.PlainText, text="Jira E-Mail"),
                element=Input(type=BlockElementType.PlainTextInput, action_id=JIRA_EMAIL_ACTION),
            ),
            DividerBlock(),
            InputBlock(
                block_id=JIRA_API_TOKEN_ACTION,
                label=Text(type=TextType.PlainText, text="Jira API Token"),
                element=Input(type=BlockElementType.PlainTextInput, action_id=JIRA_API_TOKEN_ACTION),
            ),
            ContextBlock(elements=[Text(
                type=TextType.MarkdownText,
                text="To generate Jra API Token go to https://id.atlassian.com/manage-profile/security/api-tokens")
            ]),
            DividerBlock(),
            SectionBlock(
                block_id=SELECT_USER_TEAM,
                text=Text(type=TextType.MarkdownText, text="*Select your team*"),
                accessory=SelectElement(
                    type=BlockElementType.StaticSelect,
                    action_id=SELECT_USER_TEAM,
                    placeholder=Text(type=TextType.PlainText, text="Teams"),
                    options=[Option(text=Text(type=TextType.PlainText, text=team.name),
                                    value=team.name) for team in teams]
                )
            )
            if teams else
            SectionBlock(text=Text(
                type=TextType.MarkdownText,
                text=f"*No teams available, use `{ADD_TEAM}` command to create one*"
            )),
            ActionsBlock(
                elements=[Button(
                    type=BlockElementType.Button,
                    action_id=SAVE_USER_CONFIGURATIONS,
                    text=Text(type=TextType.PlainText, text="Save"),
                    value=SAVE_USER_CONFIGURATIONS
                )]
            )
        ])
    }


def generate_home_tab_view_set_jira_keys(user: User):
    projects = get_jira_projects(user)

    if len(projects) < MAX_LEN_SLACK_SELECTOR:
        field = [
            SectionBlock(
                block_id=TYPE_OR_SELECT_USER_BOARD,
                text=Text(type=TextType.MarkdownText, text="*Select your Jira boards from the select options*"),
                accessory=SelectElement(
                    type=BlockElementType.MultiStaticSelect,
                    action_id=SELECT_USER_BOARD,
                    placeholder=Text(type=TextType.PlainText, text="Select options"),
                    options=[Option(text=Text(type=TextType.PlainText, text=project.key),
                                    value=project.key) for project in projects]
                )
            )
            if projects else
            SectionBlock(text=Text(
                type=TextType.MarkdownText,
                text="*No jira projects available*"
            )),
        ]
    else:
        field = [
            InputBlock(
                block_id=TYPE_OR_SELECT_USER_BOARD,
                label=Text(type=TextType.PlainText, text="Please write you issue keys:"),
                element=Input(type=BlockElementType.PlainTextInput, action_id=TYPE_USER_BOARD)
            ),
            ContextBlock(elements=[Text(
                type=TextType.PlainText,
                text="Please write the keys in a list like so: `EDGE,ULT` with , and no spaces")
            ]),
            ActionsBlock(
                elements=[Button(
                    type=BlockElementType.Button,
                    action_id=SAVE_USER_BOARD,
                    text=Text(type=TextType.PlainText, text="Submit"),
                    value=SAVE_USER_BOARD
                )]
            )
        ]

    return {
        "type": "home",
        "blocks": serialize_blocks([
            HeaderBlock(text=Text(type=TextType.PlainText, text="Configurations is set")),
            *field
        ])
    }


def generate_home_tab_view_user_configured():
    return {
        "type": "home",
        "blocks": serialize_blocks([
            HeaderBlock(text=Text(type=TextType.PlainText, text="Well done! Every thing is configured!")),
            SectionBlock(text=Text(
                type=TextType.MarkdownText,
                text=("Click the + button in the text area and write `daily`. "
                      "click `daily with Daily Bot` to fill out daily form.")
            )),
            ContextBlock(elements=[Text(
                type=TextType.PlainText,
                text="Other capabilities will come soon..")
            ]),
        ])
    }


def generate_user_from_config_action(body: dict) -> User:
    values = body['view']['state']['values']

    return User(
        team=values[SELECT_USER_TEAM][SELECT_USER_TEAM]['selected_option']['value'],
        jira_server_url=values[JIRA_SERVER_ACTION][JIRA_SERVER_ACTION]['value'],
        jira_api_token=values[JIRA_API_TOKEN_ACTION][JIRA_API_TOKEN_ACTION]['value'],
        jira_email=values[JIRA_EMAIL_ACTION][JIRA_EMAIL_ACTION]['value'],
        jira_host_type=values[JIRA_HOST_TYPE][JIRA_HOST_TYPE]['selected_option']['value'],
        slack_data=SlackUserData(
            team_id=body['team']['id'],
            team_domain=body['team']['domain'],
            user_id=body['user']['id'],
            user_name=body['user']['name'],
        )
    )


def generate_user_not_exists_modal():
    return {
        "type": "modal",
        "title": Text(type=TextType.PlainText, text="Daily Report").dict(exclude_none=True, by_alias=True),
        "blocks": serialize_blocks([
            HeaderBlock(text=Text(type=TextType.PlainText, text="Your user is not defined!")),
            SectionBlock(text=Text(
                type=TextType.MarkdownText,
                text=("Press the `Add apps` button in the bottom left corner (bottom of the users list) and add the "
                      "`DailyBot` app, all the configurations are in the home tab. It might not work the first time "
                      "so please try again :P")
            )),
        ])
    }


def generate_text_section_if_not_empty(text) -> List[Block]:
    return [
        SectionBlock(text=Text(type=TextType.PlainText, text=":speech_balloon: " + text, emoji=True))
    ] if text else []


def generate_issue_for_daily_message(current_user: User, user_id: str, issue: DailyIssueReport) -> List[Block]:
    return [
        SectionBlock(text=Text(type=TextType.PlainText, text=f"{issue.key} - {issue.summary}")),
        SectionBlock(
            fields=[
                Text(type=TextType.PlainText, text=issue.status),
                Text(type=TextType.MarkdownText, text=f"*<@{user_id}>*"),
            ],
            accessory=Button(
                type=BlockElementType.Button,
                action_id=OPEN_IN_JIRA,
                text=Text(type=TextType.PlainText, text="Open in Jira"),
                value=OPEN_IN_JIRA,
                url=issue.link,
            )
        ),
        *generate_text_section_if_not_empty(issue.details),
        DividerBlock(),
    ]


def generate_general_comments_with_gui(general_comments: str, user_id: str) -> List[Block]:
    if not general_comments:
        return []

    return [
        HeaderBlock(text=Text(type=TextType.PlainText, text="General Comments")),
        ContextBlock(elements=[Text(type=TextType.MarkdownText, text=f"<@{user_id}>")]),
        SectionBlock(text=Text(type=TextType.MarkdownText, text=general_comments)),
        DividerBlock(),
    ]


def generate_daily_for_user_with_gui(user: User, daily: Daily):
    return [
        [
            *([
                component
                for daily_issue in report.issue_reports
                for component in generate_issue_for_daily_message(user, user_id, daily_issue)
            ]),
            *(generate_general_comments_with_gui(report.general_comments, user_id=user_id)),
        ]
        for user_id, report in daily.reports.items()
    ]


def generate_daily_message(user: User, daily: Daily, with_gui: bool = False):
    if with_gui:
        blocks = [component for daily_report in generate_daily_for_user_with_gui(user, daily)
                  for component in daily_report]
    else:
        text = '\n'.join([
            '\n'.join([
                f"<@{user_id}>:",
                '\n'.join([
                    f" - <{issue.link}|{issue.summary}> - {issue.status}{f' - {issue.details}' if issue.details else ''}"
                    for issue in report.issue_reports
                ])
            ]) + (f"\n - {report.general_comments}" if report.general_comments else '')
            for user_id, report in daily.reports.items()])
        blocks = [SectionBlock(text=Text(type=TextType.MarkdownText, text=text))] if text else []
    return serialize_blocks([
        HeaderBlock(text=Text(type=TextType.PlainText, text=f"Daily Report for {daily.date}")),
        ContextBlock(elements=[Text(type=TextType.PlainText, text="Feel free to extend and comment in the thread.")]),
        *blocks,
    ])

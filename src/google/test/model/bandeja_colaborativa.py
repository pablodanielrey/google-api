from google.model.GoogleAuthApi import GAuthApis
import sys, os

def obtenerBandejaColaborativa(name, email):
    return {
            'whoCanPostMessage': 'ANYONE_CAN_POST',
            'showInGroupDirectory': 'true',
            'whoCanContactOwner': 'ALL_IN_DOMAIN_CAN_CONTACT',
            'customFooterText': '',
            'whoCanLeaveGroup': 'ALL_MEMBERS_CAN_LEAVE',
            'includeInGlobalAddressList': 'true',
            'messageDisplayFont': 'DEFAULT_FONT',
            'customReplyTo': '',
            'archiveOnly': 'false',
            'name': name,
            'allowExternalMembers': 'false',
            'isArchived': 'true',
            'whoCanViewMembership': 'ALL_MEMBERS_CAN_VIEW',
            'whoCanInvite': 'ALL_MANAGERS_CAN_INVITE',
            'maxMessageBytes': 26214400,
            'whoCanAdd': 'ALL_MANAGERS_CAN_ADD',
            'email': email,
            'whoCanJoin': 'INVITED_CAN_JOIN',
            'kind': 'groupsSettings#groups',
            'primaryLanguage': 'es',
            'sendMessageDenyNotification': 'false',
            'spamModerationLevel': 'MODERATE',
            'defaultMessageDenyNotificationText': '',
            'allowWebPosting': 'true',
            'whoCanViewGroup': 'ALL_MEMBERS_CAN_VIEW',
            'allowGoogleCommunication': 'true',
            'includeCustomFooter': 'false',
            'membersCanPostAsTheGroup': 'false',
            'description': '',
            'replyTo': 'REPLY_TO_LIST',
            'messageModerationLevel': 'MODERATE_NONE'}

def crearGrupo(userId, name, email):
    SCOPES = ['https://www.googleapis.com/auth/admin.directory.group']
    service = GAuthApis.getService('directory_v1', 'admin', SCOPES, userId)
    return service.groups().insert(body={'name':name, 'email':email}).execute()

if __name__ == '__main__':
    SCOPES = ['https://www.googleapis.com/auth/apps.groups.settings']
    version='v1'
    api='groupssettings'
    userId = os.environ['ADMIN_USER_GOOGLE']

    groupEmail =  sys.argv[1]
    name =  sys.argv[2]

    # group = crearGrupo(userId, name, groupEmail)

    newGroup = obtenerBandejaColaborativa(name, groupEmail)

    service = GAuthApis.getService(version, api, SCOPES, userId)
    try:
        results = service.groups().update(groupUniqueId=groupEmail, body=newGroup).execute()
        print(results)
    except:
        print('Unable to read group: {0}'.format(groupEmail))
        raise

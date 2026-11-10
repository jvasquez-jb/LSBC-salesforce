// One-off: moves portal users who were given the Portal Licensee permission set directly
// onto the Portal Licensee Access permission set group, then removes the direct assignments.
Id groupId = [SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'PortalLicenseeAccess'].Id;
List<PermissionSetAssignment> direct = [SELECT Id, AssigneeId FROM PermissionSetAssignment
    WHERE PermissionSet.Name IN ('PortalLicensee', 'DocumentChecklist') AND PermissionSetGroupId = null
      AND Assignee.ContactId != null];
Set<Id> users = new Set<Id>();
for (PermissionSetAssignment a : direct) users.add(a.AssigneeId);
for (PermissionSetAssignment a : [SELECT AssigneeId FROM PermissionSetAssignment WHERE PermissionSetGroupId = :groupId]) users.remove(a.AssigneeId);
List<PermissionSetAssignment> adds = new List<PermissionSetAssignment>();
for (Id u : users) adds.add(new PermissionSetAssignment(AssigneeId = u, PermissionSetGroupId = groupId));
insert adds;
delete direct;
System.debug(LoggingLevel.ERROR, 'MOVED ' + adds.size() + ' users; removed ' + direct.size() + ' direct assignments');

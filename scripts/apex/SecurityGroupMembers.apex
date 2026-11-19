// Fills the staff public groups (Phase 2 security). Safe to run again: it adds only missing members.
// Each desk group holds its desk's role; Inspector holds the three inspection roles; AllStaff holds every
// desk group. A person covering a second desk is added to that desk's group by hand.
Map<String, List<String>> deskRoles = new Map<String, List<String>>{
    'ExecutiveDirector' => new List<String>{ 'ExecutiveDirector' },
    'ComplianceOfficer' => new List<String>{ 'ComplianceOfficer' },
    'Finance' => new List<String>{ 'Finance' },
    'FrontDeskSupervisor' => new List<String>{ 'FrontDeskSupervisor' },
    'FrontDesk' => new List<String>{ 'FrontDesk' },
    'Mailroom' => new List<String>{ 'Mailroom' },
    'ProblemDesk' => new List<String>{ 'ProblemDesk' },
    'RenewalDesk' => new List<String>{ 'RenewalDesk' },
    'ReciprocityDesk' => new List<String>{ 'ReciprocityDesk' },
    'StudentRegistration' => new List<String>{ 'StudentRegistration' },
    'ProgramManager' => new List<String>{ 'ProgramManager' },
    'TestingDesk' => new List<String>{ 'TestingDesk' },
    'Inspector' => new List<String>{ 'InspectionSupervisor', 'ChiefInspector', 'Inspector' }
};
Set<String> roleNames = new Set<String>();
for (List<String> r : deskRoles.values()) { roleNames.addAll(r); }

Map<String, Id> roleGroup = new Map<String, Id>();
Map<Id, String> roleById = new Map<Id, String>();
for (UserRole r : [SELECT Id, DeveloperName FROM UserRole WHERE DeveloperName IN :roleNames]) { roleById.put(r.Id, r.DeveloperName); }
for (Group g : [SELECT Id, RelatedId FROM Group WHERE Type = 'Role' AND RelatedId IN :roleById.keySet()]) {
    roleGroup.put(roleById.get(g.RelatedId), g.Id);
}
Set<String> deskNames = new Set<String>(deskRoles.keySet());
deskNames.add('AllStaff');
Map<String, Id> deskGroup = new Map<String, Id>();
for (Group g : [SELECT Id, DeveloperName FROM Group WHERE Type = 'Regular' AND DeveloperName IN :deskNames]) {
    deskGroup.put(g.DeveloperName, g.Id);
}
Set<String> existing = new Set<String>();
for (GroupMember m : [SELECT GroupId, UserOrGroupId FROM GroupMember WHERE GroupId IN :deskGroup.values()]) {
    existing.add(m.GroupId + ':' + m.UserOrGroupId);
}
List<GroupMember> toAdd = new List<GroupMember>();
for (String desk : deskRoles.keySet()) {
    Id gid = deskGroup.get(desk);
    for (String role : deskRoles.get(desk)) {
        Id member = roleGroup.get(role);
        if (gid == null || member == null) { System.debug('Missing group or role: ' + desk + ' / ' + role); continue; }
        if (!existing.contains(gid + ':' + member)) { toAdd.add(new GroupMember(GroupId = gid, UserOrGroupId = member)); }
    }
    Id all = deskGroup.get('AllStaff');
    if (all != null && gid != null && !existing.contains(all + ':' + gid)) { toAdd.add(new GroupMember(GroupId = all, UserOrGroupId = gid)); }
}
insert toAdd;
System.debug('Added ' + toAdd.size() + ' group members');

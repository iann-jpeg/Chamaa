# CHAMAA Administration Architecture

## Administration levels

1. **Platform Super Admin** — platform-wide organizations, platform users, announcements and audit visibility.
2. **Organization Administrator** — organization-scoped members, cycles, approvals and reports.
3. **Cycle and operational officers** — role assignments stored by `OrganizationMembership` and `RoleAssignment`.

## Isolation

Organization dashboards load data from an active `OrganizationMembership` belonging to the logged-in user. Object URLs use the organization ID and reject memberships from another organization.

Super Admin operations are restricted to Django superusers by the `super_admin_required` view guard.

## Sensitive records

`AdministrativeAuditLog` is append-only. Django admin and application code cannot change or delete existing log rows.

`ApprovalRequest` provides an immutable workflow record for sensitive organization decisions. Sensitive actions must use an approver separate from the requester when maker-checker enforcement is enabled.

## Security notes

Create the first Super Admin using Django's secure management command or environment-provisioned process; do not place production credentials in source code.

# Changelog

## 17.0.1.0.2

Allow changing the CRM Lead of a form, for example after Lead records are merged.

Changes:
- Remove readonly from `formio.form` field `crm_lead_id`.
- Add field CRM Lead `crm_lead_id` in Form form view.

## 17.0.1.0.1

On delete CRM Lead, keep the Form (`ondelete='set null'`).

## 17.0.1.0.0

Initial release.

/** @odoo-module **/

/**
 * Face-recognition image field widget — Odoo 17 migration.
 *
 * ORIGINAL (Odoo 13/14): registered a field widget `image_recognition`
 * extending `web.basic_fields:FieldBinaryImage`, adding a "Hide/Show faces on
 * images" toggle and a custom QWeb (`core.qweb`) render of `ImageRecognition-img`.
 *
 * v17 STATUS: the legacy `web.basic_fields`, `web.field_registry`, `core.qweb`
 * and `field_utils` symbols this widget extended were REMOVED in the Odoo 15+
 * OWL rewrite. There is no `FieldBinaryImage` class to extend any more (the v17
 * image field is the OWL `ImageField` component with a completely different API),
 * so a faithful "wrapper-only" port is not possible.
 *
 * This module is therefore migrated to a CLEAN, LOADABLE ES module that:
 *   - exports the still-useful, framework-agnostic toggle helper, and
 *   - registers a tiny no-op so the `image_recognition` widget name stays known
 *     and the *.image kanban/form views that reference `widget="image_recognition"`
 *     fall back to the standard image field instead of crashing.
 *
 * The "Hide/Show faces" overlay toggle behaviour is preserved as a DOM helper
 * and wired via a document-level click handler on the legacy button class, so
 * the feature keeps working wherever the QWeb button is rendered.
 *
 * TODO (manual, advanced): re-implement as a proper OWL field component
 * extending `@web/views/fields/image/image_field:ImageField` if a bespoke
 * render of the snapshot is required. Tracked in DOCUMENTATION.md §10.
 */

import { registry } from "@web/core/registry";

/**
 * Toggle the `.only-descriptor` face-overlay layer on/off. Framework-agnostic:
 * preserved verbatim (DOM logic only) from the legacy widget.
 */
export function hideCanvasFaceRecognition() {
    document.querySelectorAll(".only-descriptor").forEach((el) => {
        el.style.display = el.style.display === "none" ? "" : "none";
    });
    document.querySelectorAll(".o-kanban-button-hide-face-recognition").forEach((btn) => {
        btn.classList.toggle("badge-success");
        btn.classList.toggle("badge-warning");
    });
}

// Delegate clicks on the legacy "Hide/Show faces on images" button so the
// overlay toggle keeps working without a custom field widget.
document.addEventListener("click", (ev) => {
    const btn = ev.target && ev.target.closest
        ? ev.target.closest("button.o-kanban-button-hide-face-recognition")
        : null;
    if (btn) {
        ev.preventDefault();
        hideCanvasFaceRecognition();
    }
});

// Keep the widget name registered (as the standard image field) so existing
// views with widget="image_recognition" do not error. The bespoke snapshot
// render is intentionally NOT reimplemented here (see header TODO).
const fieldsRegistry = registry.category("fields");
if (!fieldsRegistry.contains("image_recognition") && fieldsRegistry.contains("image")) {
    fieldsRegistry.add("image_recognition", fieldsRegistry.get("image"));
}

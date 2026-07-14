/** @odoo-module **/
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

/**
 * A list view that adds a "ربط موجود" (link existing) button right next to the
 * standard New button. The wizard to open is passed via the action context key
 * `cafm_pick_action` (an act_window xmlid). Scoped by js_class="cafm_pick_list"
 * so no other list view in the backend is affected.
 */
export class CafmPickListController extends ListController {
    async onCafmLink() {
        const xmlid = this.props.context && this.props.context.cafm_pick_action;
        if (!xmlid) {
            return;
        }
        await this.actionService.doAction(xmlid, {
            onClose: () => this.model.root.load(),
        });
    }
}
CafmPickListController.template = "care_cafm.PickListView";

registry.category("views").add("cafm_pick_list", {
    ...listView,
    Controller: CafmPickListController,
});

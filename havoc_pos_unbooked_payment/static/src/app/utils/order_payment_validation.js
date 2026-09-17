import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

/**
 * Zahlarten mit "Nicht verbuchen" (havoc_skip_accounting):
 *  - dürfen nicht mit anderen Zahlarten in einer Bestellung gemischt werden,
 *  - die Bestellung kann nicht fakturiert werden.
 * Beides wird hier vor dem Absenden geprüft, damit der Kassier sofort eine
 * verständliche Meldung bekommt statt eines Sync-Fehlers vom Server.
 */
patch(OrderPaymentValidation.prototype, {
    async isOrderValid(isForceValidate) {
        const lines = this.order.payment_ids.filter(
            (p) => !this.pos.currency.isZero(p.getAmount())
        );
        const unbooked = lines.filter((p) => p.payment_method_id.havoc_skip_accounting);
        if (unbooked.length) {
            const names = [...new Set(unbooked.map((p) => p.payment_method_id.name))].join(", ");
            if (unbooked.length !== lines.length) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Zahlarten nicht kombinierbar"),
                    body: _t(
                        "Die Zahlart %s wird nicht verbucht und kann daher nicht mit anderen Zahlarten in einer Bestellung kombiniert werden. Bitte nur eine Zahlart verwenden.",
                        names
                    ),
                });
                return false;
            }
            if (this.order.isToInvoice()) {
                this.pos.dialog.add(AlertDialog, {
                    title: _t("Keine Rechnung möglich"),
                    body: _t(
                        "Bestellungen mit der Zahlart %s werden nicht verbucht und können daher nicht fakturiert werden. Bitte die Rechnungsoption deaktivieren oder eine andere Zahlart wählen.",
                        names
                    ),
                });
                return false;
            }
        }
        return super.isOrderValid(...arguments);
    },
});

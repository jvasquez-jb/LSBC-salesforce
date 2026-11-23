import { LightningElement, api, track } from 'lwc';
import { FlowAttributeChangeEvent } from 'lightning/flowSupport';
import getItems from '@salesforce/apex/DocumentChecklistUploadController.getItems';
import addFileSlot from '@salesforce/apex/DocumentChecklistUploadController.addFileSlot';
import removeFile from '@salesforce/apex/DocumentChecklistUploadController.removeFile';

// Display wording for each checklist status. Only presentation: the flow owns every status change.
const STATUS_TEXT = {
    New: 'Not uploaded yet',
    Pending: 'Uploaded, waiting for the Board to review',
    Accepted: 'Accepted',
    Rejected: 'Returned by the Board'
};

// Documents that reach the Board by mail or straight from another state or company. The applicant may upload a copy
// so review can start, but the official document still has to arrive as the instruction says.
const SENT_TO_BOARD_TEXT = 'Provide it as the instruction says (by mail, sent straight from another state or organization, or shown at the inspection). You can submit without it. If you have a copy, you may upload it here so we can start reviewing; the official document must still reach the Board.';

const OPEN = new Set(['New', 'Rejected']);

export default class DocumentChecklistUpload extends LightningElement {
    @api applicationId;
    @api includeCategories;
    @api excludeCategories;
    @api uploadedItemIds = [];
    // Staff entering a paper application can upload documents that are sent to the Board. Off on the portal.
    @api allowSentToBoard = false;

    @track groups = [];
    loading = true;
    busy = false;
    errorMessage;
    // The file whose Remove was clicked and is waiting for Yes or No.
    confirmKey;
    // The checklist items last read from the server.
    items = [];

    connectedCallback() {
        this.load();
    }

    get hasItems() {
        return this.groups.length > 0;
    }

    get noItemsMessage() {
        return !this.loading && !this.errorMessage && !this.hasItems ? 'There are no documents to upload for this application.' : undefined;
    }

    get showSpinner() {
        return this.loading || this.busy;
    }

    setUploaded(ids) {
        this.uploadedItemIds = [...ids];
        this.dispatchEvent(new FlowAttributeChangeEvent('uploadedItemIds', this.uploadedItemIds));
    }

    async load() {
        this.loading = true;
        try {
            const items = await getItems({
                applicationId: this.applicationId,
                includeCategories: this.includeCategories,
                excludeCategories: this.excludeCategories
            });
            const uploaded = new Set(this.uploadedItemIds || []);
            // An item holding a file staff haven't seen (on a New item, or added to a returned item after it was returned)
            // was uploaded in an earlier visit, or the upload finished after Next was clicked: count it as uploaded so
            // the flow sets it to Pending and lets the applicant continue. A returned item's old file doesn't count.
            const before = uploaded.size;
            items.forEach((item) => {
                if (item.hasNewFile) uploaded.add(item.id);
            });
            if (uploaded.size !== before) this.setUploaded(uploaded);
            this.items = items;
            this.buildGroups();
            this.errorMessage = undefined;
        } catch (e) {
            this.errorMessage = 'Your documents could not be loaded. Refresh the page, or call the Board at 225-756-3404.';
        } finally {
            this.loading = false;
        }
    }

    // Builds the rows from the items last loaded.
    buildGroups() {
        const items = this.items || [];
        const uploaded = new Set(this.uploadedItemIds || []);
        // Salesforce allows one file per checklist item, so extra files for a document sit on extra items. They are
        // shown inside their original item's row. An extra item whose original isn't listed gets its own row.
        const ids = new Set(items.map((item) => item.id));
        const extras = new Map();
        items.forEach((item) => {
            if (item.primaryItemId && ids.has(item.primaryItemId)) {
                if (!extras.has(item.primaryItemId)) extras.set(item.primaryItemId, []);
                extras.get(item.primaryItemId).push(item);
            }
        });

        const byCategory = new Map();
        items.forEach((item) => {
            if (item.primaryItemId && ids.has(item.primaryItemId)) return;
            if (!byCategory.has(item.category)) byCategory.set(item.category, []);
            byCategory.get(item.category).push(this.buildRow(item, extras.get(item.id) || [], uploaded));
        });
        this.groups = [...byCategory.entries()].map(([name, rows]) => ({ name, rows }));
    }

    buildRow(item, extraItems, uploaded) {
        const hasFile = (i) => i.files && i.files.length > 0;
        const justUploaded = [item, ...extraItems].some((i) => uploaded.has(i.id));
        const shownStatus = justUploaded && item.status !== 'Accepted' ? 'Pending' : item.status;
        const anyFile = hasFile(item) || extraItems.some(hasFile);
        const sentToBoard = item.isSentToBoard && !this.allowSentToBoard && item.status === 'New' && !anyFile;
        const returned = item.status === 'Rejected';

        // Every file in the row, from the original item first, then its extra items. Whether a file can be removed is
        // decided by the server (own uploads for portal users, any file for staff, never once accepted).
        const files = [];
        [item, ...extraItems].forEach((i) => {
            (i.files || []).forEach((f) => {
                const key = i.id + ':' + f.contentDocumentId;
                files.push({
                    key,
                    itemId: i.id,
                    contentDocumentId: f.contentDocumentId,
                    name: f.name,
                    canRemove: f.canRemove,
                    removeLabel: returned ? 'Replace file' : 'Remove',
                    removeAlt: (returned ? 'Replace ' : 'Remove ') + f.name,
                    confirming: this.confirmKey === key,
                    confirmText: returned ? 'Take ' + f.name + ' off so you can upload a new file?' : 'Remove ' + f.name + '?'
                });
            });
        });

        // Upload boxes: the original item while it has no file (New or Returned), and each empty extra item, which
        // also has Cancel. A Pending or Accepted item already holds its file, even when the portal user can't see it.
        const slots = [];
        if (OPEN.has(item.status) && !hasFile(item)) slots.push({ itemId: item.id, label: item.name, isExtra: false });
        extraItems.forEach((i) => {
            if (OPEN.has(i.status) && !hasFile(i)) slots.push({ itemId: i.id, label: item.name + ' (another file)', isExtra: true });
        });

        return {
            ...item,
            requiredText: item.isSentToBoard ? 'Sent to the Board' : item.isRequired ? 'Required' : 'Optional',
            requiredClass: item.isSentToBoard ? 'lsbc-badge lsbc-badge_board' : item.isRequired ? 'lsbc-badge lsbc-badge_required' : 'lsbc-badge',
            statusText: sentToBoard ? SENT_TO_BOARD_TEXT : STATUS_TEXT[shownStatus] || shownStatus,
            statusClass: 'lsbc-status lsbc-status_' + (shownStatus || 'New').toLowerCase(),
            isReturned: returned && !!item.comments,
            files,
            hasFiles: files.length > 0,
            slots,
            hasSlots: slots.length > 0,
            // Add another file: offered once the row holds a file, while no empty extra box is already showing.
            canAddFile: item.canAddFile && !slots.some((s) => s.isExtra)
        };
    }

    handleUploadFinished(event) {
        const ids = new Set(this.uploadedItemIds || []);
        ids.add(event.target.dataset.id);
        this.setUploaded(ids);
        this.load();
    }

    async handleAddFile(event) {
        await this.run(() => addFileSlot({ itemId: event.currentTarget.dataset.id }));
    }

    handleRemoveClick(event) {
        this.confirmKey = event.currentTarget.dataset.key;
        this.buildGroups();
    }

    handleRemoveCancel() {
        this.confirmKey = undefined;
        this.buildGroups();
    }

    async handleRemoveConfirm(event) {
        const { itemId, documentId } = event.currentTarget.dataset;
        this.confirmKey = undefined;
        const ids = new Set(this.uploadedItemIds || []);
        ids.delete(itemId);
        await this.run(() => removeFile({ itemId, contentDocumentId: documentId }), ids);
    }

    async handleSlotCancel(event) {
        const itemId = event.currentTarget.dataset.id;
        const ids = new Set(this.uploadedItemIds || []);
        ids.delete(itemId);
        await this.run(() => removeFile({ itemId, contentDocumentId: null }), ids);
    }

    // Runs a server action, then reloads. The server's message is shown when it refuses.
    async run(action, uploadedAfter) {
        this.busy = true;
        try {
            await action();
            if (uploadedAfter) this.setUploaded(uploadedAfter);
            this.errorMessage = undefined;
        } catch (e) {
            this.errorMessage = (e && e.body && e.body.message) || 'That did not work. Refresh the page and try again, or call the Board at 225-756-3404.';
        } finally {
            this.busy = false;
        }
        const message = this.errorMessage;
        await this.load();
        this.errorMessage = message;
    }
}

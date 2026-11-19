import { LightningElement, api, track } from 'lwc';
import { FlowAttributeChangeEvent } from 'lightning/flowSupport';
import getItems from '@salesforce/apex/DocumentChecklistUploadController.getItems';

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

export default class DocumentChecklistUpload extends LightningElement {
    @api applicationId;
    @api includeCategories;
    @api excludeCategories;
    @api uploadedItemIds = [];
    // Staff entering a paper application can upload documents that are sent to the Board. Off on the portal.
    @api allowSentToBoard = false;

    @track groups = [];
    loading = true;
    errorMessage;

    connectedCallback() {
        this.load();
    }

    get hasItems() {
        return this.groups.length > 0;
    }

    get noItemsMessage() {
        return !this.loading && !this.errorMessage && !this.hasItems ? 'There are no documents to upload for this application.' : undefined;
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
            // An item that holds a file but is still New (or Returned) was uploaded in an earlier visit, or the upload
            // finished after Next was clicked: count it as uploaded so the flow sets it to Pending and lets the
            // applicant continue.
            const before = uploaded.size;
            items.forEach((item) => {
                if ((item.status === 'New' || item.status === 'Rejected') && item.fileNames && item.fileNames.length) uploaded.add(item.id);
            });
            if (uploaded.size !== before) {
                this.uploadedItemIds = [...uploaded];
                this.dispatchEvent(new FlowAttributeChangeEvent('uploadedItemIds', this.uploadedItemIds));
            }
            const byCategory = new Map();
            items.forEach((item) => {
                if (!byCategory.has(item.category)) byCategory.set(item.category, []);
                const justUploaded = uploaded.has(item.id);
                const shownStatus = justUploaded && item.status !== 'Accepted' ? 'Pending' : item.status;
                const sentToBoard = item.isSentToBoard && !this.allowSentToBoard && item.status === 'New' && !(item.fileNames && item.fileNames.length);
                byCategory.get(item.category).push({
                    ...item,
                    requiredText: item.isSentToBoard ? 'Sent to the Board' : item.isRequired ? 'Required' : 'Optional',
                    requiredClass: item.isSentToBoard ? 'lsbc-badge lsbc-badge_board' : item.isRequired ? 'lsbc-badge lsbc-badge_required' : 'lsbc-badge',
                    statusText: sentToBoard ? SENT_TO_BOARD_TEXT : STATUS_TEXT[shownStatus] || shownStatus,
                    statusClass: 'lsbc-status lsbc-status_' + (shownStatus || 'New').toLowerCase(),
                    isReturned: shownStatus === 'Rejected' && !!item.comments,
                    // Salesforce allows one file per checklist item: no upload box once an item holds a file.
                    // A returned item's file is moved to the application by the checklist trigger, which frees it.
                    // Only New and Returned (Rejected) items can take a file: a Pending or Accepted item already holds one,
                    // even when the portal user can't see it (a file staff uploaded is visible to staff only).
                    // Documents sent to the Board take an optional copy, on the portal as well as for staff.
                    canUpload: (item.status === 'New' || item.status === 'Rejected') && !(item.fileNames && item.fileNames.length),
                    hasFiles: item.fileNames && item.fileNames.length > 0,
                    filesText: (item.fileNames || []).join(', ')
                });
            });
            this.groups = [...byCategory.entries()].map(([name, rows]) => ({ name, rows }));
            this.errorMessage = undefined;
        } catch (e) {
            this.errorMessage = 'Your documents could not be loaded. Refresh the page, or call the Board at 225-756-3404.';
        } finally {
            this.loading = false;
        }
    }

    handleUploadFinished(event) {
        const itemId = event.target.dataset.id;
        const ids = new Set(this.uploadedItemIds || []);
        ids.add(itemId);
        this.uploadedItemIds = [...ids];
        this.dispatchEvent(new FlowAttributeChangeEvent('uploadedItemIds', this.uploadedItemIds));
        this.load();
    }
}

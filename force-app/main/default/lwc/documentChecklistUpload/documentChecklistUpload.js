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

// Documents that reach the Board by mail or straight from another state or company: no upload here.
const SENT_TO_BOARD_TEXT = 'Not uploaded here: send it to the Board as the instruction says. Staff add it when it arrives, and you can submit without it.';

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
                    canUpload: item.status !== 'Accepted' && (!item.isSentToBoard || this.allowSentToBoard),
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

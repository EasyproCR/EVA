export class ConversationStore {
    constructor({ maxTurns, ttlMs, maxActiveUsers }) {
        this.maxTurns = maxTurns;
        this.ttlMs = ttlMs;
        this.maxActiveUsers = maxActiveUsers;
        this.byUser = new Map();
    }

    _now() {
        return Date.now();
    }

    _touch(userId) {
        const entry = this.byUser.get(userId);
        if (entry) entry.lastSeen = this._now();
    }

    _ensureCapacity() {
        if (this.byUser.size <= this.maxActiveUsers) return;

        // Evict least recently seen users until under cap.
        const entries = Array.from(this.byUser.entries());
        entries.sort((a, b) => (a[1].lastSeen ?? 0) - (b[1].lastSeen ?? 0));

        while (this.byUser.size > this.maxActiveUsers && entries.length) {
            const [userId] = entries.shift();
            this.byUser.delete(userId);
        }
    }

    cleanupExpired() {
        const now = this._now();
        for (const [userId, entry] of this.byUser.entries()) {
            if (now - entry.lastSeen > this.ttlMs) {
                this.byUser.delete(userId);
            }
        }
    }

    getMessages(userId) {
        const entry = this.byUser.get(userId);
        if (!entry) return [];
        return entry.messages;
    }

    ensureUser(userId) {
        if (!this.byUser.has(userId)) {
            this.byUser.set(userId, { messages: [], lastSeen: this._now() });
            this._ensureCapacity();
        } else {
            this._touch(userId);
        }
    }

    appendUserMessage(userId, content) {
        this.ensureUser(userId);
        const entry = this.byUser.get(userId);
        entry.messages.push({ role: "user", content, timestamp: new Date() });
        this.prune(userId);
        this._touch(userId);
    }

    appendAssistantMessage(userId, content) {
        this.ensureUser(userId);
        const entry = this.byUser.get(userId);
        entry.messages.push({ role: "assistant", content, timestamp: new Date() });
        this.prune(userId);
        this._touch(userId);
    }

    prune(userId) {
        const entry = this.byUser.get(userId);
        if (!entry) return;
        const overflow = entry.messages.length - this.maxTurns;
        if (overflow > 0) {
            entry.messages.splice(0, overflow);
        }
    }

    deleteUser(userId) {
        this.byUser.delete(userId);
    }
}

"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.makeInternalErrorMessage = makeInternalErrorMessage;
/** @internal */
function makeInternalErrorMessage(err) {
    if (err == null || typeof err !== 'object') {
        return String(err);
    }
    else if (typeof err.message === 'string') {
        return err.message;
    }
    else {
        return JSON.stringify(err);
    }
}
//# sourceMappingURL=makeInternalErrorMessage.js.map
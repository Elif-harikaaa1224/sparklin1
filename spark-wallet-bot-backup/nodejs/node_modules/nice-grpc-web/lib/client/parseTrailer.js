"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseTrailer = parseTrailer;
const nice_grpc_common_1 = require("nice-grpc-common");
/** @internal */
function parseTrailer(trailer) {
    let status;
    const statusValue = trailer.get('grpc-status');
    if (statusValue != null) {
        const statusNum = +statusValue;
        if (statusNum in nice_grpc_common_1.Status) {
            status = statusNum;
        }
        else {
            throw new Error(`Received invalid status code from server: ${statusValue}`);
        }
    }
    else {
        throw new Error('Received no status code from server');
    }
    let message = trailer.get('grpc-message');
    if (message != null) {
        try {
            message = decodeURIComponent(message);
        }
        catch (_a) {
            // ignore
        }
    }
    const trailerCopy = (0, nice_grpc_common_1.Metadata)(trailer);
    trailerCopy.delete('grpc-status');
    trailerCopy.delete('grpc-message');
    return {
        status,
        message,
        trailer: trailerCopy,
    };
}
//# sourceMappingURL=parseTrailer.js.map
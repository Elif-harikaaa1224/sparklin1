"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.concatBuffers = concatBuffers;
/** @internal */
function concatBuffers(buffers, totalLength) {
    if (buffers.length === 1) {
        return buffers[0];
    }
    const result = new Uint8Array(totalLength);
    let offset = 0;
    for (const buffer of buffers) {
        result.set(buffer, offset);
        offset += buffer.length;
    }
    return result;
}
//# sourceMappingURL=concatBuffers.js.map
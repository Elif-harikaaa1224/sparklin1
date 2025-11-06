"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LPM_HEADER_LENGTH = void 0;
exports.parseLpmHeader = parseLpmHeader;
exports.encodeFrame = encodeFrame;
/**
 * Length-Prefixed-Message → Compressed-Flag Message-Length Message
 * Compressed-Flag → 0 / 1 # encoded as 1 byte unsigned integer
 * Message-Length → {length of Message} # encoded as 4 byte unsigned integer (big endian)
 * Message → *{binary octet}
 *
 * https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md
 *
 * For gRPC-Web the 8th (MSB) bit of the 1st gRPC frame byte also indicates
 * whether the message represents metadata.
 *
 * https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-WEB.md
 *
 * @internal
 */
exports.LPM_HEADER_LENGTH = 5;
/** @internal */
function parseLpmHeader(data) {
    if (data.length !== exports.LPM_HEADER_LENGTH) {
        throw new Error(`Invalid LPM header length: ${data.length}`);
    }
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    const compressed = (view.getUint8(0) & 1) !== 0;
    const isMetadata = (view.getUint8(0) & 0x80) !== 0;
    const length = view.getUint32(1);
    return {
        compressed,
        isMetadata,
        length,
    };
}
/** @internal */
function encodeFrame(data) {
    const messageBytes = new Uint8Array(exports.LPM_HEADER_LENGTH + data.length);
    new DataView(messageBytes.buffer, 1, 4).setUint32(0, data.length, false);
    messageBytes.set(data, exports.LPM_HEADER_LENGTH);
    return messageBytes;
}
//# sourceMappingURL=framing.js.map
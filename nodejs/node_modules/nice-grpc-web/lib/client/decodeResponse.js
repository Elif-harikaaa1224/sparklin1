"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.decodeResponse = decodeResponse;
const concatBuffers_1 = require("../utils/concatBuffers");
const decodeMetadata_1 = require("./decodeMetadata");
const framing_1 = require("./framing");
/** @internal */
async function* decodeResponse({ response, decode, onHeader, onTrailer, }) {
    let receivedHeader = false;
    let receivedTrailer = false;
    let receivedData = false;
    let buffer = createChunkBuffer(framing_1.LPM_HEADER_LENGTH);
    let lpmHeader;
    for await (const frame of response) {
        if (frame.type === 'header') {
            handleHeader(frame.header);
        }
        else if (frame.type === 'trailer') {
            handleTrailer(frame.trailer);
        }
        else if (frame.type === 'data') {
            if (receivedTrailer) {
                throw new Error('Received data after trailer');
            }
            let { data } = frame;
            while (data.length > 0 || (lpmHeader === null || lpmHeader === void 0 ? void 0 : lpmHeader.length) === 0) {
                const position = Math.min(data.length, buffer.targetLength - buffer.totalLength);
                const chunk = data.subarray(0, position);
                data = data.subarray(position);
                buffer.chunks.push(chunk);
                buffer.totalLength += chunk.length;
                if (buffer.totalLength === buffer.targetLength) {
                    const messageBytes = (0, concatBuffers_1.concatBuffers)(buffer.chunks, buffer.totalLength);
                    if (lpmHeader == null) {
                        lpmHeader = (0, framing_1.parseLpmHeader)(messageBytes);
                        buffer = createChunkBuffer(lpmHeader.length);
                    }
                    else {
                        if (lpmHeader.compressed) {
                            throw new Error('Compressed messages not supported');
                        }
                        if (lpmHeader.isMetadata) {
                            if (!receivedHeader) {
                                handleHeader((0, decodeMetadata_1.decodeMetadata)(messageBytes));
                            }
                            else {
                                handleTrailer((0, decodeMetadata_1.decodeMetadata)(messageBytes));
                            }
                        }
                        else {
                            if (!receivedHeader) {
                                throw new Error('Received data before header');
                            }
                            yield decode(messageBytes);
                            receivedData = true;
                        }
                        lpmHeader = undefined;
                        buffer = createChunkBuffer(framing_1.LPM_HEADER_LENGTH);
                    }
                }
            }
        }
    }
    function handleHeader(header) {
        if (receivedHeader) {
            throw new Error('Received multiple headers');
        }
        if (receivedData) {
            throw new Error('Received header after data');
        }
        if (receivedTrailer) {
            throw new Error('Received header after trailer');
        }
        receivedHeader = true;
        onHeader(header);
    }
    function handleTrailer(trailer) {
        if (receivedTrailer) {
            throw new Error('Received multiple trailers');
        }
        receivedTrailer = true;
        onTrailer(trailer);
    }
    function createChunkBuffer(targetLength) {
        return {
            chunks: [],
            totalLength: 0,
            targetLength,
        };
    }
}
//# sourceMappingURL=decodeResponse.js.map
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.decodeMetadata = decodeMetadata;
const nice_grpc_common_1 = require("nice-grpc-common");
const js_base64_1 = require("js-base64");
/** @internal */
function decodeMetadata(data) {
    const metadata = (0, nice_grpc_common_1.Metadata)();
    const text = new TextDecoder().decode(data);
    for (const line of text.split('\r\n')) {
        if (!line) {
            continue;
        }
        const splitIndex = line.indexOf(':');
        if (splitIndex === -1) {
            throw new Error(`Invalid metadata line: ${line}`);
        }
        const key = line.slice(0, splitIndex).trim().toLowerCase();
        const value = line.slice(splitIndex + 1).trim();
        if (key.endsWith('-bin')) {
            for (const item of value.split(/,\s?/)) {
                metadata.append(key, js_base64_1.Base64.toUint8Array(item));
            }
        }
        else {
            metadata.append(key, value);
        }
    }
    return metadata;
}
//# sourceMappingURL=decodeMetadata.js.map
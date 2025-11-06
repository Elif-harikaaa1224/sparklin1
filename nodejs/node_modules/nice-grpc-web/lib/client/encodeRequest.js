"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.encodeRequest = encodeRequest;
const framing_1 = require("./framing");
/** @internal */
async function* encodeRequest({ request, encode, }) {
    for await (const data of request) {
        const bytes = encode(data);
        yield (0, framing_1.encodeFrame)(bytes);
    }
}
//# sourceMappingURL=encodeRequest.js.map
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FetchTransport = FetchTransport;
const abort_controller_x_1 = require("abort-controller-x");
const js_base64_1 = require("js-base64");
const nice_grpc_common_1 = require("nice-grpc-common");
/**
 * Transport for browsers based on `fetch` API.
 */
function FetchTransport(config) {
    return async function* fetchTransport({ url, body, metadata, signal, method }) {
        let requestBody;
        if (!method.requestStream) {
            let bodyBuffer;
            for await (const chunk of body) {
                bodyBuffer = chunk;
                break;
            }
            requestBody = bodyBuffer;
        }
        else {
            let iterator;
            requestBody = new ReadableStream({
                type: 'bytes',
                start() {
                    iterator = body[Symbol.asyncIterator]();
                },
                async pull(controller) {
                    const { done, value } = await iterator.next();
                    if (done) {
                        controller.close();
                    }
                    else {
                        controller.enqueue(value);
                    }
                },
                async cancel() {
                    var _a, _b;
                    await ((_b = (_a = iterator).return) === null || _b === void 0 ? void 0 : _b.call(_a));
                },
            });
        }
        const response = await fetch(url, {
            method: 'POST',
            body: requestBody,
            headers: metadataToHeaders(metadata),
            signal,
            cache: config === null || config === void 0 ? void 0 : config.cache,
            ['duplex']: 'half',
            credentials: config === null || config === void 0 ? void 0 : config.credentials,
        });
        yield {
            type: 'header',
            header: headersToMetadata(response.headers),
        };
        if (!response.ok) {
            const responseText = await response.text();
            throw new nice_grpc_common_1.ClientError(method.path, getStatusFromHttpCode(response.status), getErrorDetailsFromHttpResponse(response.status, responseText));
        }
        (0, abort_controller_x_1.throwIfAborted)(signal);
        const reader = response.body.getReader();
        const abortListener = () => {
            reader.cancel().catch(() => { });
        };
        signal.addEventListener('abort', abortListener);
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (value != null) {
                    yield {
                        type: 'data',
                        data: value,
                    };
                }
                if (done) {
                    break;
                }
            }
        }
        finally {
            signal.removeEventListener('abort', abortListener);
            (0, abort_controller_x_1.throwIfAborted)(signal);
        }
    };
}
function metadataToHeaders(metadata) {
    const headers = new Headers();
    for (const [key, values] of metadata) {
        for (const value of values) {
            headers.append(key, typeof value === 'string' ? value : js_base64_1.Base64.fromUint8Array(value));
        }
    }
    return headers;
}
function headersToMetadata(headers) {
    const metadata = new nice_grpc_common_1.Metadata();
    for (const [key, value] of headers) {
        if (key.endsWith('-bin')) {
            for (const item of value.split(/,\s?/)) {
                metadata.append(key, js_base64_1.Base64.toUint8Array(item));
            }
        }
        else {
            metadata.set(key, value);
        }
    }
    return metadata;
}
function getStatusFromHttpCode(statusCode) {
    switch (statusCode) {
        case 400:
            return nice_grpc_common_1.Status.INTERNAL;
        case 401:
            return nice_grpc_common_1.Status.UNAUTHENTICATED;
        case 403:
            return nice_grpc_common_1.Status.PERMISSION_DENIED;
        case 404:
            return nice_grpc_common_1.Status.UNIMPLEMENTED;
        case 429:
        case 502:
        case 503:
        case 504:
            return nice_grpc_common_1.Status.UNAVAILABLE;
        default:
            return nice_grpc_common_1.Status.UNKNOWN;
    }
}
function getErrorDetailsFromHttpResponse(statusCode, responseText) {
    return (`Received HTTP ${statusCode} response: ` +
        (responseText.length > 1000
            ? responseText.slice(0, 1000) + '... (truncated)'
            : responseText));
}
//# sourceMappingURL=fetch.js.map
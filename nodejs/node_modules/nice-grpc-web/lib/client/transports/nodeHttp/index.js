"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.NodeHttpTransport = NodeHttpTransport;
const abort_controller_x_1 = require("abort-controller-x");
const assert_1 = __importDefault(require("assert"));
const http_1 = __importDefault(require("http"));
const https_1 = __importDefault(require("https"));
const js_base64_1 = require("js-base64");
const nice_grpc_common_1 = require("nice-grpc-common");
/**
 * Transport for NodeJS based on `http` and `https` modules.
 *
 * Note that for NodeJS 18+ you can use the default `FetchTransport`.
 */
function NodeHttpTransport() {
    return async function* nodeHttpTransport({ url, body, metadata, signal, method, }) {
        let bodyBuffer;
        let pipeAbortController;
        if (!method.requestStream) {
            for await (const chunk of body) {
                bodyBuffer = chunk;
                break;
            }
            (0, assert_1.default)(bodyBuffer != null);
        }
        else {
            pipeAbortController = new AbortController();
        }
        const { res, removeAbortListener } = await new Promise((resolve, reject) => {
            const abortListener = () => {
                pipeAbortController === null || pipeAbortController === void 0 ? void 0 : pipeAbortController.abort();
                req.destroy();
            };
            const req = (url.startsWith('https://') ? https_1.default : http_1.default).request(url, {
                method: 'POST',
                headers: metadataToHeaders(metadata),
            }, res => {
                resolve({
                    res,
                    removeAbortListener() {
                        signal.removeEventListener('abort', abortListener);
                    },
                });
            });
            signal.addEventListener('abort', abortListener);
            req.on('error', err => {
                reject(err);
            });
            if (bodyBuffer != null) {
                req.setHeader('Content-Length', bodyBuffer.byteLength);
                req.write(bodyBuffer);
                req.end();
            }
            else {
                pipeBody(pipeAbortController.signal, body, req).then(() => {
                    req.end();
                }, err => {
                    req.destroy(err);
                });
            }
        }).catch(err => {
            (0, abort_controller_x_1.throwIfAborted)(signal);
            throw err;
        });
        yield {
            type: 'header',
            header: headersToMetadata(res.headers),
        };
        if (res.statusCode < 200 || res.statusCode >= 300) {
            const responseText = await new Promise((resolve, reject) => {
                let text = '';
                res.on('data', chunk => {
                    text += chunk;
                });
                res.on('error', err => {
                    reject(err);
                });
                res.on('end', () => {
                    resolve(text);
                });
            });
            throw new nice_grpc_common_1.ClientError(method.path, getStatusFromHttpCode(res.statusCode), getErrorDetailsFromHttpResponse(res.statusCode, responseText));
        }
        try {
            for await (const data of res) {
                yield {
                    type: 'data',
                    data,
                };
            }
        }
        finally {
            pipeAbortController === null || pipeAbortController === void 0 ? void 0 : pipeAbortController.abort();
            removeAbortListener();
            (0, abort_controller_x_1.throwIfAborted)(signal);
        }
    };
}
function metadataToHeaders(metadata) {
    const headers = {};
    for (const [key, values] of metadata) {
        headers[key] = values.map(value => typeof value === 'string' ? value : js_base64_1.Base64.fromUint8Array(value));
    }
    return headers;
}
function headersToMetadata(headers) {
    const metadata = new nice_grpc_common_1.Metadata();
    for (const [key, headerValue] of Object.entries(headers)) {
        if (headerValue == null) {
            continue;
        }
        const value = Array.isArray(headerValue)
            ? headerValue
            : headerValue.split(/,\s?/);
        if (key.endsWith('-bin')) {
            for (const item of value) {
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
async function pipeBody(signal, body, request) {
    request.flushHeaders();
    for await (const item of body) {
        (0, abort_controller_x_1.throwIfAborted)(signal);
        const shouldContinue = request.write(item);
        if (!shouldContinue) {
            await (0, abort_controller_x_1.waitForEvent)(signal, request, 'drain');
        }
    }
}
//# sourceMappingURL=index.js.map
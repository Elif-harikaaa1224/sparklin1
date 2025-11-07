"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.NodeHttpTransport = exports.WebsocketTransport = exports.FetchTransport = exports.Status = exports.Metadata = exports.composeClientMiddleware = exports.ClientError = void 0;
var nice_grpc_common_1 = require("nice-grpc-common");
Object.defineProperty(exports, "ClientError", { enumerable: true, get: function () { return nice_grpc_common_1.ClientError; } });
Object.defineProperty(exports, "composeClientMiddleware", { enumerable: true, get: function () { return nice_grpc_common_1.composeClientMiddleware; } });
Object.defineProperty(exports, "Metadata", { enumerable: true, get: function () { return nice_grpc_common_1.Metadata; } });
Object.defineProperty(exports, "Status", { enumerable: true, get: function () { return nice_grpc_common_1.Status; } });
__exportStar(require("./service-definitions"), exports);
__exportStar(require("./client/channel"), exports);
__exportStar(require("./client/ClientFactory"), exports);
__exportStar(require("./client/Client"), exports);
var fetch_1 = require("./client/transports/fetch");
Object.defineProperty(exports, "FetchTransport", { enumerable: true, get: function () { return fetch_1.FetchTransport; } });
var websocket_1 = require("./client/transports/websocket");
Object.defineProperty(exports, "WebsocketTransport", { enumerable: true, get: function () { return websocket_1.WebsocketTransport; } });
var nodeHttp_1 = require("./client/transports/nodeHttp");
Object.defineProperty(exports, "NodeHttpTransport", { enumerable: true, get: function () { return nodeHttp_1.NodeHttpTransport; } });
//# sourceMappingURL=index.js.map
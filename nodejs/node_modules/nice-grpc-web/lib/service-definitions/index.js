"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.normalizeServiceDefinition = normalizeServiceDefinition;
const grpc_web_1 = require("./grpc-web");
const ts_proto_1 = require("./ts-proto");
/** @internal */
function normalizeServiceDefinition(definition) {
    if ((0, grpc_web_1.isGrpcWebServiceDefinition)(definition)) {
        return (0, grpc_web_1.fromGrpcWebServiceDefinition)(definition);
    }
    else if ((0, ts_proto_1.isTsProtoServiceDefinition)(definition)) {
        return (0, ts_proto_1.fromTsProtoServiceDefinition)(definition);
    }
    else {
        return definition;
    }
}
//# sourceMappingURL=index.js.map
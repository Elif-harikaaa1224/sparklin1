"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createUnaryMethod = createUnaryMethod;
const nice_grpc_common_1 = require("nice-grpc-common");
const asyncIterableOf_1 = require("../utils/asyncIterableOf");
const isAsyncIterable_1 = require("../utils/isAsyncIterable");
const makeCall_1 = require("./makeCall");
/** @internal */
function createUnaryMethod(definition, channel, middleware, defaultOptions) {
    const methodDescriptor = {
        path: definition.path,
        requestStream: definition.requestStream,
        responseStream: definition.responseStream,
        options: definition.options,
    };
    async function* unaryMethod(request, options) {
        if ((0, isAsyncIterable_1.isAsyncIterable)(request)) {
            throw new Error('A middleware passed invalid request to next(): expected a single message for unary method');
        }
        const response = (0, makeCall_1.makeCall)(definition, channel, (0, asyncIterableOf_1.asyncIterableOf)(request), options);
        let unaryResponse;
        for await (const message of response) {
            if (unaryResponse != null) {
                throw new nice_grpc_common_1.ClientError(definition.path, nice_grpc_common_1.Status.INTERNAL, 'Received more than one message from server for unary method');
            }
            unaryResponse = message;
        }
        if (unaryResponse == null) {
            throw new nice_grpc_common_1.ClientError(definition.path, nice_grpc_common_1.Status.INTERNAL, 'Server did not return a response');
        }
        return unaryResponse;
    }
    const method = middleware == null
        ? unaryMethod
        : (request, options) => middleware({
            method: methodDescriptor,
            requestStream: false,
            request,
            responseStream: false,
            next: unaryMethod,
        }, options);
    return async (request, options) => {
        const iterable = method(request, {
            ...defaultOptions,
            ...options,
        });
        const iterator = iterable[Symbol.asyncIterator]();
        let result = await iterator.next();
        while (true) {
            if (!result.done) {
                result = await iterator.throw(new Error('A middleware yielded a message, but expected to only return a message for unary method'));
                continue;
            }
            if (result.value == null) {
                result = await iterator.throw(new Error('A middleware returned void, but expected to return a message for unary method'));
                continue;
            }
            return result.value;
        }
    };
}
//# sourceMappingURL=createUnaryMethod.js.map
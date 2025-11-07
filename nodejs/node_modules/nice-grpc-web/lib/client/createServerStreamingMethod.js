"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createServerStreamingMethod = createServerStreamingMethod;
const asyncIterableOf_1 = require("../utils/asyncIterableOf");
const isAsyncIterable_1 = require("../utils/isAsyncIterable");
const makeCall_1 = require("./makeCall");
/** @internal */
function createServerStreamingMethod(definition, channel, middleware, defaultOptions) {
    const methodDescriptor = {
        path: definition.path,
        requestStream: definition.requestStream,
        responseStream: definition.responseStream,
        options: definition.options,
    };
    async function* serverStreamingMethod(request, options) {
        if ((0, isAsyncIterable_1.isAsyncIterable)(request)) {
            throw new Error('A middleware passed invalid request to next(): expected a single message for server streaming method');
        }
        const response = (0, makeCall_1.makeCall)(definition, channel, (0, asyncIterableOf_1.asyncIterableOf)(request), options);
        yield* response;
    }
    const method = middleware == null
        ? serverStreamingMethod
        : (request, options) => middleware({
            method: methodDescriptor,
            requestStream: false,
            request,
            responseStream: true,
            next: serverStreamingMethod,
        }, options);
    return (request, options) => {
        const iterable = method(request, {
            ...defaultOptions,
            ...options,
        });
        const iterator = iterable[Symbol.asyncIterator]();
        return {
            [Symbol.asyncIterator]() {
                return {
                    async next() {
                        const result = await iterator.next();
                        if (result.done && result.value != null) {
                            return await iterator.throw(new Error('A middleware returned a message, but expected to return void for server streaming method'));
                        }
                        return result;
                    },
                    return() {
                        return iterator.return();
                    },
                    throw(err) {
                        return iterator.throw(err);
                    },
                };
            },
        };
    };
}
//# sourceMappingURL=createServerStreamingMethod.js.map
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createBidiStreamingMethod = createBidiStreamingMethod;
const isAsyncIterable_1 = require("../utils/isAsyncIterable");
const makeCall_1 = require("./makeCall");
/** @internal */
function createBidiStreamingMethod(definition, channel, middleware, defaultOptions) {
    const methodDescriptor = {
        path: definition.path,
        requestStream: definition.requestStream,
        responseStream: definition.responseStream,
        options: definition.options,
    };
    async function* bidiStreamingMethod(request, options) {
        if (!(0, isAsyncIterable_1.isAsyncIterable)(request)) {
            throw new Error('A middleware passed invalid request to next(): expected a single message for bidirectional streaming method');
        }
        const response = (0, makeCall_1.makeCall)(definition, channel, request, options);
        yield* response;
    }
    const method = middleware == null
        ? bidiStreamingMethod
        : (request, options) => middleware({
            method: methodDescriptor,
            requestStream: true,
            request,
            responseStream: true,
            next: bidiStreamingMethod,
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
                            return await iterator.throw(new Error('A middleware returned a message, but expected to return void for bidirectional streaming method'));
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
//# sourceMappingURL=createBidiStreamingMethod.js.map
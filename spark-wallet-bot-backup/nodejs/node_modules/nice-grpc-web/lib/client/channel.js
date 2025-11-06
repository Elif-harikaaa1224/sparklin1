"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createChannel = createChannel;
const fetch_1 = require("./transports/fetch");
/**
 * Creates a new channel.
 *
 * @param address The address of the server, in the form `protocol://host:port`,
 *     where `protocol` is one of `http` or `https`. If the port is not
 *     specified, it will be inferred from the protocol.
 * @param transport The transport to use for the channel. If not specified, the
 *     default transport based on `fetch` will be used. Other supported
 *     transports include `WebsocketTransport` (works only with `grpcwebproxy`)
 *     and `NodeHttpTransport` (works only in NodeJS).
 */
function createChannel(address, transport = (0, fetch_1.FetchTransport)()) {
    return { address, transport };
}
//# sourceMappingURL=channel.js.map
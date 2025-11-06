import { Transport } from '../Transport';
export interface FetchTransportConfig {
    credentials?: RequestCredentials;
    cache?: RequestCache;
}
/**
 * Transport for browsers based on `fetch` API.
 */
export declare function FetchTransport(config?: FetchTransportConfig): Transport;

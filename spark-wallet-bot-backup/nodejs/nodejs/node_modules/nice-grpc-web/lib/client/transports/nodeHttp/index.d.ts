import { Transport } from '../../Transport';
/**
 * Transport for NodeJS based on `http` and `https` modules.
 *
 * Note that for NodeJS 18+ you can use the default `FetchTransport`.
 */
export declare function NodeHttpTransport(): Transport;

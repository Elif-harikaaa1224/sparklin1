import { CompatServiceDefinition, MethodDefinition, ServiceDefinition } from '.';
export interface GrpcWebServiceDefinition {
    serviceName: string;
}
export interface GrpcWebMethodDefinition<TRequest extends ProtobufMessage, TResponse extends ProtobufMessage> {
    methodName: string;
    service: GrpcWebServiceDefinition;
    requestStream: boolean;
    responseStream: boolean;
    requestType: ProtobufMessageClass<TRequest>;
    responseType: ProtobufMessageClass<TResponse>;
}
export interface GrpcWebUnaryMethodDefinition<TRequest extends ProtobufMessage, TResponse extends ProtobufMessage> extends GrpcWebMethodDefinition<TRequest, TResponse> {
    requestStream: false;
    responseStream: false;
}
export interface ProtobufMessageClass<T extends ProtobufMessage> {
    new (): T;
    deserializeBinary(bytes: Uint8Array): T;
}
export interface ProtobufMessage {
    toObject(): {};
    serializeBinary(): Uint8Array;
}
export type FromGrpcWebServiceDefinition<Service extends GrpcWebServiceDefinition> = {
    [M in GrpcWebServiceMethodKeys<Service> as Uncapitalize<M>]: FromGrpcWebMethodDefinition<Service[M]>;
};
export type GrpcWebServiceMethodKeys<Service extends GrpcWebServiceDefinition> = {
    [K in keyof Service]: Service[K] extends GrpcWebMethodDefinition<any, any> ? K : never;
}[keyof Service] & string;
export type FromGrpcWebMethodDefinition<Method> = Method extends GrpcWebMethodDefinition<infer Request, infer Response> ? MethodDefinition<Request, Request, Response, Response, Method['requestStream'], Method['responseStream']> : never;
export declare function fromGrpcWebServiceDefinition(definition: GrpcWebServiceDefinition): ServiceDefinition;
export declare function isGrpcWebServiceDefinition(definition: CompatServiceDefinition): definition is GrpcWebServiceDefinition;

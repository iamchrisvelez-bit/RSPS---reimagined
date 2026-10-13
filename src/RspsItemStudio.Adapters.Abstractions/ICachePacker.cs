namespace RspsItemStudio.Adapters.Abstractions;

public interface ICachePacker
{
    AdapterResult<IntegrationReport> PackToStaging(ExportStagingRequest request);
    AdapterResult<IntegrationReport> PackToLiveTree(ExportStagingRequest request);
}

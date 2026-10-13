using System.Numerics;
using System.Runtime.InteropServices;
using RspsItemStudio.Core.Meshes;
using Veldrid;

namespace RspsItemStudio.Rendering;

public sealed class VeldridViewportController : IDisposable
{
    private readonly ViewportCamera _camera = new();
    private GraphicsDevice? _device;
    private CommandList? _commandList;
    private Pipeline? _meshPipelineSolid;
    private Pipeline? _meshPipelineWireframe;
    private Pipeline? _gridPipeline;
    private ResourceSet? _meshResourceSet;
    private ResourceSet? _gridResourceSet;
    private DeviceBuffer? _frameUniformBuffer;
    private DeviceBuffer? _meshVertexBuffer;
    private DeviceBuffer? _meshIndexBuffer;
    private DeviceBuffer? _gridVertexBuffer;
    private DeviceBuffer? _gridIndexBuffer;
    private uint _meshIndexCount;
    private uint _gridIndexCount;
    private ViewportDisplayMode _displayMode = ViewportDisplayMode.Solid;
    private int _width = 1;
    private int _height = 1;
    private bool _meshLoaded;
    private StudioMesh? _pendingMesh;

    public ViewportCamera Camera => _camera;

    public void Attach(IntPtr hwnd, int width, int height)
    {
        if (_device is not null)
            return;

        _width = Math.Max(1, width);
        _height = Math.Max(1, height);

        var options = new GraphicsDeviceOptions
        {
            PreferStandardClipSpaceYDirection = true,
            PreferDepthRangeZeroToOne = true,
            SyncToVerticalBlank = true,
            ResourceBindingModel = ResourceBindingModel.Improved
        };

        var swapchain = new SwapchainDescription(
            SwapchainSource.CreateWin32(hwnd, GetModuleHandle(null)),
            (uint)_width,
            (uint)_height,
            PixelFormat.B8_G8_R8_A8_UNorm,
            true);

        _device = GraphicsDevice.CreateD3D11(options, swapchain);
        _commandList = _device.ResourceFactory.CreateCommandList();
        CreateResources();
        Resize(_width, _height);

        if (_pendingMesh is not null)
        {
            LoadMesh(_pendingMesh);
            _pendingMesh = null;
        }
    }

    public void Resize(int width, int height)
    {
        if (_device is null || width < 1 || height < 1)
            return;

        _width = width;
        _height = height;
        _device.ResizeMainWindow((uint)width, (uint)height);
        _camera.SetAspect(width / (float)height);
    }

    public void SetDisplayMode(ViewportDisplayMode mode) =>
        _displayMode = mode;

    public void LoadMesh(StudioMesh mesh)
    {
        if (_device is null)
        {
            _pendingMesh = mesh;
            return;
        }

        var (vertices, indices, min, max) = MeshGeometryBuilder.Build(mesh);
        _meshIndexCount = (uint)indices.Length;
        _meshLoaded = _meshIndexCount > 0;

        if (_meshVertexBuffer is not null)
        {
            _meshVertexBuffer.Dispose();
            _meshIndexBuffer?.Dispose();
        }

        var factory = _device.ResourceFactory;
        _meshVertexBuffer = factory.CreateBuffer(
            new BufferDescription(
                (uint)(vertices.Length * Marshal.SizeOf<MeshGeometryBuilder.Vertex>()),
                BufferUsage.VertexBuffer));
        _meshIndexBuffer = factory.CreateBuffer(
            new BufferDescription((uint)(indices.Length * sizeof(uint)), BufferUsage.IndexBuffer));

        _device.UpdateBuffer(_meshVertexBuffer, 0, vertices);
        _device.UpdateBuffer(_meshIndexBuffer, 0, indices);

        if (_meshLoaded)
            _camera.FitBounds(min, max);
    }

    public void Render()
    {
        if (_device is null || _commandList is null)
            return;

        UpdateUniforms();

        _commandList.Begin();
        _commandList.SetFramebuffer(_device.SwapchainFramebuffer);
        _commandList.ClearColorTarget(0, new RgbaFloat(0.12f, 0.12f, 0.14f, 1f));
        _commandList.ClearDepthStencil(1f);

        DrawGrid();
        DrawMesh();

        _commandList.End();
        _device.SubmitCommands(_commandList);
        _device.SwapBuffers();
    }

    public void Dispose()
    {
        _meshIndexBuffer?.Dispose();
        _meshVertexBuffer?.Dispose();
        _gridIndexBuffer?.Dispose();
        _gridVertexBuffer?.Dispose();
        _frameUniformBuffer?.Dispose();
        _meshResourceSet?.Dispose();
        _gridResourceSet?.Dispose();
        _meshPipelineSolid?.Dispose();
        _meshPipelineWireframe?.Dispose();
        _gridPipeline?.Dispose();
        _commandList?.Dispose();
        _device?.Dispose();
    }

    private void CreateResources()
    {
        if (_device is null)
            return;

        var factory = _device.ResourceFactory;
        _frameUniformBuffer = factory.CreateBuffer(
            new BufferDescription((uint)Marshal.SizeOf<FrameUniforms>(), BufferUsage.UniformBuffer));

        var (gridVerts, gridIndices) = MeshGeometryBuilder.BuildGrid();
        _gridIndexCount = (uint)gridIndices.Length;
        _gridVertexBuffer = factory.CreateBuffer(
            new BufferDescription(
                (uint)(gridVerts.Length * Marshal.SizeOf<MeshGeometryBuilder.Vertex>()),
                BufferUsage.VertexBuffer));
        _gridIndexBuffer = factory.CreateBuffer(
            new BufferDescription((uint)(gridIndices.Length * sizeof(uint)), BufferUsage.IndexBuffer));
        _device.UpdateBuffer(_gridVertexBuffer, 0, gridVerts);
        _device.UpdateBuffer(_gridIndexBuffer, 0, gridIndices);

        var meshVertexLayout = new VertexLayoutDescription(
            new VertexElementDescription("Position", VertexElementSemantic.Position, VertexElementFormat.Float3),
            new VertexElementDescription("Normal", VertexElementSemantic.Normal, VertexElementFormat.Float3),
            new VertexElementDescription("TexCoord", VertexElementSemantic.TextureCoordinate, VertexElementFormat.Float2));

        var gridVertexLayout = new VertexLayoutDescription(
            new VertexElementDescription("Position", VertexElementSemantic.Position, VertexElementFormat.Float3));

        var (meshVs, meshFs) = VeldridShaders.CreateMeshShaders(factory);
        var (gridVs, gridFs) = VeldridShaders.CreateGridShaders(factory);

        var resourceLayout = factory.CreateResourceLayout(
            new ResourceLayoutDescription(
                new ResourceLayoutElementDescription("FrameBlock", ResourceKind.UniformBuffer, ShaderStages.Vertex | ShaderStages.Fragment)));

        _meshResourceSet = factory.CreateResourceSet(new ResourceSetDescription(resourceLayout, _frameUniformBuffer));
        _gridResourceSet = factory.CreateResourceSet(new ResourceSetDescription(resourceLayout, _frameUniformBuffer));

        var meshShaders = new[] { meshVs, meshFs };
        var gridShaders = new[] { gridVs, gridFs };

        var outputs = _device.SwapchainFramebuffer.OutputDescription;
        _meshPipelineSolid = CreateMeshPipeline(factory, meshShaders, meshVertexLayout, resourceLayout, PolygonFillMode.Solid, outputs);
        _meshPipelineWireframe = CreateMeshPipeline(factory, meshShaders, meshVertexLayout, resourceLayout, PolygonFillMode.Wireframe, outputs);
        _gridPipeline = factory.CreateGraphicsPipeline(new GraphicsPipelineDescription
        {
            BlendState = BlendStateDescription.SingleOverrideBlend,
            DepthStencilState = DepthStencilStateDescription.DepthOnlyLessEqual,
            RasterizerState = new RasterizerStateDescription(
                FaceCullMode.None,
                PolygonFillMode.Solid,
                FrontFace.Clockwise,
                true,
                false),
            PrimitiveTopology = PrimitiveTopology.LineList,
            ResourceLayouts = new[] { resourceLayout },
            ShaderSet = new ShaderSetDescription(new[] { gridVertexLayout }, gridShaders),
            Outputs = _device.SwapchainFramebuffer.OutputDescription
        });

        foreach (var shader in meshShaders.Concat(gridShaders))
            shader.Dispose();
    }

    private static Pipeline CreateMeshPipeline(
        ResourceFactory factory,
        Shader[] shaders,
        VertexLayoutDescription vertexLayout,
        ResourceLayout resourceLayout,
        PolygonFillMode fillMode,
        OutputDescription outputs) =>
        factory.CreateGraphicsPipeline(new GraphicsPipelineDescription
        {
            BlendState = BlendStateDescription.SingleOverrideBlend,
            DepthStencilState = DepthStencilStateDescription.DepthOnlyLessEqual,
            RasterizerState = new RasterizerStateDescription(
                FaceCullMode.Back,
                fillMode,
                FrontFace.Clockwise,
                true,
                false),
            PrimitiveTopology = PrimitiveTopology.TriangleList,
            ResourceLayouts = new[] { resourceLayout },
            ShaderSet = new ShaderSetDescription(new[] { vertexLayout }, shaders),
            Outputs = outputs
        });

    private void DrawGrid()
    {
        if (_device is null || _commandList is null || _gridPipeline is null ||
            _gridVertexBuffer is null || _gridIndexBuffer is null || _gridResourceSet is null)
            return;

        _commandList.SetPipeline(_gridPipeline);
        _commandList.SetGraphicsResourceSet(0, _gridResourceSet);
        _commandList.SetVertexBuffer(0, _gridVertexBuffer);
        _commandList.SetIndexBuffer(_gridIndexBuffer, IndexFormat.UInt32);
        _commandList.DrawIndexed(_gridIndexCount, 1, 0, 0, 0);
    }

    private void DrawMesh()
    {
        if (!_meshLoaded || _device is null || _commandList is null ||
            _meshVertexBuffer is null || _meshIndexBuffer is null || _meshResourceSet is null)
            return;

        var pipeline = _displayMode == ViewportDisplayMode.Wireframe
            ? _meshPipelineWireframe
            : _meshPipelineSolid;
        if (pipeline is null)
            return;

        _commandList.SetPipeline(pipeline);
        _commandList.SetGraphicsResourceSet(0, _meshResourceSet);
        _commandList.SetVertexBuffer(0, _meshVertexBuffer);
        _commandList.SetIndexBuffer(_meshIndexBuffer, IndexFormat.UInt32);
        _commandList.DrawIndexed(_meshIndexCount, 1, 0, 0, 0);
    }

    private void UpdateUniforms()
    {
        if (_device is null || _frameUniformBuffer is null)
            return;

        var modeValue = _displayMode switch
        {
            ViewportDisplayMode.Solid => 0f,
            ViewportDisplayMode.SolidUntextured => 1f,
            ViewportDisplayMode.Wireframe => 2f,
            _ => 0f
        };

        var uniforms = new FrameUniforms
        {
            View = _camera.GetViewMatrix(),
            Projection = _camera.GetProjectionMatrix(),
            LightAndMode = new Vector4(-0.35f, -0.85f, -0.4f, modeValue)
        };

        _device.UpdateBuffer(_frameUniformBuffer, 0, uniforms);
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr GetModuleHandle(string? lpModuleName);
}

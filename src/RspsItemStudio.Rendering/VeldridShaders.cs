using System.Text;
using Veldrid;
using Veldrid.SPIRV;

namespace RspsItemStudio.Rendering;

internal static class VeldridShaders
{
    private const string VertexShaderGlsl = """
        #version 450
        layout(set = 0, binding = 0) uniform FrameBlock {
            mat4 View;
            mat4 Projection;
            vec4 LightAndMode;
        } frame;

        layout(location = 0) in vec3 Position;
        layout(location = 1) in vec3 Normal;
        layout(location = 2) in vec2 TexCoord;

        layout(location = 0) out vec3 vNormal;
        layout(location = 1) out vec2 vUv;
        layout(location = 2) flat out float vMode;

        void main() {
            gl_Position = frame.Projection * frame.View * vec4(Position, 1.0);
            vNormal = Normal;
            vUv = TexCoord;
            vMode = frame.LightAndMode.w;
        }
        """;

    private const string FragmentShaderGlsl = """
        #version 450
        layout(set = 0, binding = 0) uniform FrameBlock {
            mat4 View;
            mat4 Projection;
            vec4 LightAndMode;
        } frame;

        layout(location = 0) in vec3 vNormal;
        layout(location = 1) in vec2 vUv;
        layout(location = 2) flat in float vMode;

        layout(location = 0) out vec4 outColor;

        void main() {
            vec3 lightDir = normalize(-frame.LightAndMode.xyz);
            vec3 n = normalize(vNormal);
            float ndl = max(dot(n, lightDir), 0.12);

            if (vMode < 0.5) {
                vec3 albedo = vec3(0.78, 0.74, 0.70);
                albedo *= 0.85 + 0.15 * sin(vUv.x * 12.0) * cos(vUv.y * 12.0);
                outColor = vec4(albedo * ndl, 1.0);
            } else if (vMode < 1.5) {
                outColor = vec4(vec3(0.72) * ndl, 1.0);
            } else {
                outColor = vec4(vec3(0.55) * ndl, 1.0);
            }
        }
        """;

    private const string GridVertexGlsl = """
        #version 450
        layout(set = 0, binding = 0) uniform FrameBlock {
            mat4 View;
            mat4 Projection;
            vec4 LightAndMode;
        } frame;

        layout(location = 0) in vec3 Position;

        void main() {
            gl_Position = frame.Projection * frame.View * vec4(Position, 1.0);
        }
        """;

    private const string GridFragmentGlsl = """
        #version 450
        layout(location = 0) out vec4 outColor;

        void main() {
            outColor = vec4(0.28, 0.30, 0.34, 1.0);
        }
        """;

    public static (Shader Vertex, Shader Fragment) CreateMeshShaders(ResourceFactory factory)
    {
        var compileOptions = new GlslCompileOptions();
        var vs = SpirvCompilation.CompileGlslToSpirv(
            VertexShaderGlsl, "main", ShaderStages.Vertex, compileOptions);
        var fs = SpirvCompilation.CompileGlslToSpirv(
            FragmentShaderGlsl, "main", ShaderStages.Fragment, compileOptions);

        return (
            factory.CreateShader(new ShaderDescription(ShaderStages.Vertex, vs.SpirvBytes, "main")),
            factory.CreateShader(new ShaderDescription(ShaderStages.Fragment, fs.SpirvBytes, "main")));
    }

    public static (Shader Vertex, Shader Fragment) CreateGridShaders(ResourceFactory factory)
    {
        var compileOptions = new GlslCompileOptions();
        var vs = SpirvCompilation.CompileGlslToSpirv(
            GridVertexGlsl, "main", ShaderStages.Vertex, compileOptions);
        var fs = SpirvCompilation.CompileGlslToSpirv(
            GridFragmentGlsl, "main", ShaderStages.Fragment, compileOptions);

        return (
            factory.CreateShader(new ShaderDescription(ShaderStages.Vertex, vs.SpirvBytes, "main")),
            factory.CreateShader(new ShaderDescription(ShaderStages.Fragment, fs.SpirvBytes, "main")));
    }
}

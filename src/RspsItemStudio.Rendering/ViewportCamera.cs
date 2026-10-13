using System.Numerics;

namespace RspsItemStudio.Rendering;

public sealed class ViewportCamera
{
    private float _yaw = 0.6f;
    private float _pitch = 0.35f;
    private float _distance = 4f;
    private Vector3 _target = Vector3.Zero;
    private float _aspect = 1f;

    public float Yaw => _yaw;
    public float Pitch => _pitch;
    public float Distance => _distance;
    public Vector3 Target => _target;

    public void SetAspect(float aspect) =>
        _aspect = Math.Max(0.01f, aspect);

    public void Orbit(float deltaYaw, float deltaPitch)
    {
        _yaw += deltaYaw;
        _pitch += deltaPitch;
        const float limit = 1.45f;
        _pitch = Math.Clamp(_pitch, -limit, limit);
    }

    public void Pan(float deltaX, float deltaY)
    {
        var (right, up) = GetCameraBasis();
        var scale = _distance * 0.002f;
        _target -= right * deltaX * scale;
        _target += up * deltaY * scale;
    }

    public void Zoom(float delta)
    {
        _distance *= 1f - delta * 0.1f;
        _distance = Math.Clamp(_distance, 0.25f, 200f);
    }

    public void FitBounds(Vector3 min, Vector3 max)
    {
        var center = (min + max) * 0.5f;
        var extent = max - min;
        var radius = extent.Length() * 0.5f;
        if (radius < 0.001f)
            radius = 1f;

        _target = center;
        _distance = Math.Max(radius * 2.5f, 1f);
    }

    public Matrix4x4 GetViewMatrix()
    {
        var offset = SphericalOffset();
        var eye = _target + offset;
        return Matrix4x4.CreateLookAt(eye, _target, Vector3.UnitY);
    }

    public Matrix4x4 GetProjectionMatrix() =>
        Matrix4x4.CreatePerspectiveFieldOfView(
            MathF.PI / 4f,
            _aspect,
            0.05f,
            500f);

    private Vector3 SphericalOffset()
    {
        var cosPitch = MathF.Cos(_pitch);
        return new Vector3(
            _distance * cosPitch * MathF.Sin(_yaw),
            _distance * MathF.Sin(_pitch),
            _distance * cosPitch * MathF.Cos(_yaw));
    }

    private (Vector3 Right, Vector3 Up) GetCameraBasis()
    {
        var view = GetViewMatrix();
        var right = Vector3.Normalize(new Vector3(view.M11, view.M21, view.M31));
        var up = Vector3.Normalize(new Vector3(view.M12, view.M22, view.M32));
        return (right, up);
    }
}

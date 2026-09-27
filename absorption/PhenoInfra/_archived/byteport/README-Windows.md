# BytePort Windows Deployment Platform

## 🚀 Overview

BytePort has been successfully adapted for Windows 11 deployment! This version transforms your existing GitHub-to-AWS deployment pipeline into a powerful local Windows server with public URL access through Cloudflare tunnels.

## 🏗️ Architecture Changes

### Original vs Windows Architecture

| Component | Original (AWS) | Windows Adaptation |
|-----------|----------------|-------------------|
| **Compute** | EC2 Instances | Docker Containers |
| **Storage** | S3 Buckets | Local File System |
| **Networking** | ALB/VPC | Cloudflare Tunnels |
| **DNS** | Route 53 | Cloudflare DNS |
| **Cost** | Pay-per-use | Hardware + Domain only |

### Key Benefits
✅ **Zero Cloud Costs** - No AWS charges, unlimited deployments
✅ **Same UI/UX** - Familiar BytePort interface and workflow
✅ **Public URLs** - Cloudflare tunnels provide global access
✅ **Local Control** - Full control over deployment environment
✅ **Proven Architecture** - Based on your working BytePort design

## 📋 Prerequisites

### System Requirements
- **OS**: Windows 11 Pro (recommended for Hyper-V support)
- **RAM**: 16GB+ (for multiple containers)
- **Storage**: 500GB+ SSD
- **Network**: Stable internet with good upload speed
- **Permissions**: Administrator privileges

### Required Accounts
- **Cloudflare Account** with domain
- **GitHub Account** (existing)

## 🛠️ Quick Setup

### 1. Automated Setup
```powershell
# Run as Administrator
.\setup-windows.ps1 -Domain "yourdomain.com"
```

### 2. Manual Cloudflare Configuration
```powershell
# Authenticate with Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create byteport-main

# Copy credentials to C:\BytePort\tunnels\
```

### 3. Start Services
```powershell
# Start all BytePort services
.\start-services.bat
```

## 🔧 Configuration

### Environment Variables
The setup script automatically configures:
- `BYTEPORT_ROOT=C:\BytePort`
- `BYTEPORT_DOMAIN=yourdomain.com`
- `PROJECTS_PATH=C:\BytePort\projects`
- `TUNNEL_CONFIG_PATH=C:\BytePort\tunnels`

### Project Configuration
Projects still use the same `odin.nvms` format:
```yaml
NAME: "my-project"
DESCRIPTION: "My awesome project"
SERVICES:
  - NAME: "main"
    PATH: "./frontend"
    PORT: 8080
  - NAME: "api"
    PATH: "./backend"
    PORT: 8081
```

## 🚀 Usage

### Deploying Projects

1. **Access BytePort**: Navigate to `http://localhost:5173`
2. **Login**: Use existing credentials
3. **Select Repository**: Choose from GitHub repos
4. **Deploy**: Click deploy and wait for completion
5. **Access**: Get public URL via Cloudflare tunnel

### Managing Deployments

#### View Running Projects
```powershell
# List Docker containers
docker ps --filter "name=byteport-"

# Check tunnel status
cloudflared tunnel info byteport-main
```

#### Project Logs
- **Application Logs**: `C:\BytePort\logs\`
- **Tunnel Logs**: `C:\BytePort\logs\tunnel.log`
- **Container Logs**: `docker logs byteport-projectname-servicename`

#### Stop/Remove Projects
Use the BytePort UI termination feature, or manually:
```powershell
# Stop project containers
docker stop byteport-projectname-main
docker stop byteport-projectname-api

# Remove containers
docker rm byteport-projectname-main
docker rm byteport-projectname-api
```

## 🔍 Technical Details

### New Components Added

#### Docker Manager (`lib/docker.go`)
- Container lifecycle management
- Automatic Dockerfile generation
- Port allocation and networking
- Multi-language support (Node.js, Go, Python, Rust)

#### Tunnel Manager (`lib/tunnel.go`)
- Cloudflare tunnel configuration
- Dynamic ingress rule generation
- Process management
- SSL termination

#### Storage Manager (`lib/storage.go`)
- Local file system management
- Project isolation
- Backup and cleanup
- Archive extraction

### Deployment Flow

1. **Repository Clone** → Local storage
2. **Container Build** → Docker image creation
3. **Service Start** → Container deployment
4. **Tunnel Setup** → Public URL generation
5. **Health Check** → Service verification

### Port Management
- **API**: 8081 (BytePort main API)
- **NVMS**: 3000 (Deployment service)
- **Frontend**: 5173 (SvelteKit dev server)
- **Projects**: 8080+ (Dynamic allocation)

## 🔒 Security

### Network Security
- Docker network isolation
- Cloudflare DDoS protection
- SSL/TLS termination
- No inbound port requirements

### Access Control
- GitHub OAuth integration
- Session-based authentication
- Project-level permissions
- Secure credential storage

## 🐛 Troubleshooting

### Common Issues

#### Docker Containers Won't Start
```powershell
# Check Docker status
docker version

# Restart Docker service
Restart-Service docker

# Check container logs
docker logs byteport-projectname-servicename
```

#### Tunnel Connection Issues
```powershell
# Test tunnel connectivity
cloudflared tunnel --config C:\BytePort\tunnels\config.yml run --loglevel debug

# Check DNS resolution
nslookup yourdomain.com
```

#### Port Conflicts
```powershell
# Check port usage
netstat -ano | findstr :8081

# Kill process using port
taskkill /PID <PID> /F
```

### Log Analysis
```powershell
# View recent tunnel logs
Get-Content C:\BytePort\logs\tunnel.log -Tail 50

# Monitor logs in real-time
Get-Content C:\BytePort\logs\tunnel.log -Wait
```

## 📈 Performance Optimization

### Resource Allocation
- **Docker Desktop**: Allocate 8GB+ RAM
- **CPU**: Use all available cores
- **Storage**: Use SSD for project storage

### Container Optimization
- Multi-stage Docker builds
- Health check implementation
- Resource limit enforcement

## 🔄 Backup & Recovery

### Automated Backup
```powershell
# Create project backup
$backupPath = "C:\BytePort\backups\$(Get-Date -Format 'yyyy-MM-dd-HH-mm')"
New-Item -ItemType Directory -Path $backupPath
Copy-Item -Recurse C:\BytePort\projects\* $backupPath\
```

### Recovery Process
1. Stop all services
2. Restore project files
3. Rebuild Docker images
4. Restart services

## 🎯 Testing Your Setup

### Test with Existing Projects
Your existing projects should work immediately:
- **fixit-go**: Go-based application
- **chatta**: Chat application

### Verification Steps
1. Deploy a simple project
2. Check container status
3. Verify tunnel connectivity
4. Test public URL access
5. Confirm termination works

## 📞 Support

### Getting Help
1. Check logs in `C:\BytePort\logs\`
2. Verify Docker and tunnel status
3. Test with simple projects first
4. Review original BytePort docs for core functionality

### Known Limitations
- Windows-only deployment
- Requires stable internet for tunnels
- Docker Desktop dependency

## 🎊 Success Metrics

Your BytePort Windows adaptation is successful when:
- ✅ Projects deploy without errors
- ✅ Public URLs are accessible
- ✅ Containers start and run properly
- ✅ Termination cleans up resources
- ✅ Multiple projects can run simultaneously

## 🚀 Next Steps

1. **Deploy Test Projects**: Start with your existing fixit-go and chatta
2. **Monitor Performance**: Track resource usage and response times
3. **Scale Horizontally**: Add more Windows servers if needed
4. **Implement CI/CD**: Set up automated deployments
5. **Add Monitoring**: Implement comprehensive logging and alerting

---

**Congratulations!** You now have a fully functional Windows-based deployment platform that maintains all the power and simplicity of your original BytePort design while eliminating cloud costs and providing complete local control.

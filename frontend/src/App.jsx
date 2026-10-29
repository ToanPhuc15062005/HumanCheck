import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Shield,
  Activity,
  Camera,
  Layers,
  Crosshair,
  RotateCcw,
  Download,
  Users,
  UserPlus,
  UserMinus,
  Gauge,
  Sun,
  Moon,
  Sliders,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  Wifi,
  WifiOff,
  Maximize2,
  Play,
  Pause,
  RefreshCw,
  VideoOff,
  Globe,
  X
} from 'lucide-react';

export default function App() {
  // Backend Telemetry State
  const [stats, setStats] = useState({
    count_in: 0,
    count_out: 0,
    inside: 0,
    active_objects_count: 0,
    fps: 0.0,
    is_night_mode: false,
    is_paused: false,
    mean_luminance: 100.0,
    camera_status: 'online',
    active_source: '',
    resolution: [320, 240],
    dropped_frames: 0,
    tripwire: { pt1: [80, 160], pt2: [280, 160], d_threshold: 35.0 },
    events: []
  });

  const [connected, setConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [activeTab, setActiveTab] = useState('video'); // 'video' | 'mask'
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [dThreshold, setDThreshold] = useState(35.0);
  const [toastMessage, setToastMessage] = useState(null);
  const [showConfigDrawer, setShowConfigDrawer] = useState(false);

  // Device Management State
  const [devices, setDevices] = useState([]);
  const [activeSource, setActiveSource] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [showRtspModal, setShowRtspModal] = useState(false);
  const [rtspInput, setRtspInput] = useState('');
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  // Canvas drawing state for tripwire
  const canvasRef = useRef(null);
  const viewportRef = useRef(null);
  const dragStartRef = useRef(null);
  const isDraggingRef = useRef(false);
  const lastEditTimeRef = useRef(0);
  const [currentLine, setCurrentLine] = useState({ pt1: [80, 160], pt2: [280, 160] });
  const [isDragging, setIsDragging] = useState(false);

  const API_BASE = window.location.port === '5173' ? 'http://localhost:8000' : '';
  const WS_URL = window.location.port === '5173'
    ? 'ws://localhost:8000/ws/stats'
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/stats`;

  // Dynamic Native Video Resolution
  const nativeW = stats.resolution && stats.resolution[0] > 0 ? stats.resolution[0] : 320;
  const nativeH = stats.resolution && stats.resolution[1] > 0 ? stats.resolution[1] : 240;

  // Show Swiss Minimalist Toast
  const triggerToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  // Device Discovery & Fetch
  const fetchDevices = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/devices`);
      if (res.ok) {
        const data = await res.json();
        if (data.devices) {
          setDevices(data.devices);
          if (data.active_source !== undefined) {
            setActiveSource(String(data.active_source));
          }
        }
      }
    } catch (e) {
      console.warn('Could not fetch devices list', e);
    }
  }, [API_BASE]);

  // Scan hardware devices
  const handleScanDevices = async () => {
    setIsScanning(true);
    triggerToast('Đang quét các cổng camera phần cứng...');
    try {
      const res = await fetch(`${API_BASE}/api/v1/devices/scan`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setDevices(data.devices || []);
        triggerToast(`Đã tìm thấy ${data.devices?.length || 0} thiết bị camera/video`);
      }
    } catch (e) {
      triggerToast('Quét thiết bị thất bại');
    } finally {
      setIsScanning(false);
    }
  };

  // Switch Video Source
  const handleSwitchSource = async (newSource) => {
    if (newSource === 'CUSTOM_RTSP') {
      setShowRtspModal(true);
      return;
    }

    triggerToast(`Đang chuyển sang nguồn: ${newSource}...`);
    try {
      const res = await fetch(`${API_BASE}/api/v1/devices/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: newSource })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setActiveSource(String(newSource));
        setStreamError(false);
        setStreamKey(Date.now());
        triggerToast(`Kết nối thành công tới ${newSource}`);
      } else {
        triggerToast(data.message || 'Không thể chuyển đổi nguồn camera');
      }
    } catch (e) {
      triggerToast('Lỗi khi gửi yêu cầu chuyển camera');
    }
  };

  // Submit custom RTSP URL
  const handleConnectRtsp = async (e) => {
    e.preventDefault();
    if (!rtspInput.trim()) return;
    setShowRtspModal(false);
    await handleSwitchSource(rtspInput.trim());
    setRtspInput('');
  };

  const handleTogglePlayback = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/stream/toggle`, { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        const nextState = json.data?.is_paused ?? !isPaused;
        setIsPaused(nextState);
        triggerToast(nextState ? 'Video stream paused' : 'Video stream resumed');
      }
    } catch (e) {
      setIsPaused(!isPaused);
      triggerToast('Playback toggle requested');
    }
  };

  // Retry Stream when interrupted
  const handleRetryStream = () => {
    setStreamError(false);
    setStreamKey(Date.now());
    triggerToast('Đang làm mới luồng video...');
  };

  // 1. Initial Config Fetch & WebSocket Setup
  useEffect(() => {
    fetchDevices();

    // Fetch initial config
    fetch(`${API_BASE}/api/v1/config`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) {
          setCurrentLine({ pt1: data.pt1, pt2: data.pt2 });
          setDThreshold(data.d_threshold || 35.0);
          if (data.video_source) {
            setActiveSource(String(data.video_source));
          }
        }
      })
      .catch(() => {});

    // WebSocket Stream
    let socket = null;
    let reconnectTimeout = null;

    const connectWebSocket = () => {
      try {
        socket = new WebSocket(WS_URL);

        socket.onopen = () => {
          setConnected(true);
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setStats(data);
            if (data.is_paused !== undefined) {
              setIsPaused(data.is_paused);
            }
            if (data.active_source !== undefined) {
              setActiveSource(String(data.active_source));
            }
            if (
              data.tripwire &&
              !isDraggingRef.current &&
              Date.now() - lastEditTimeRef.current > 2500
            ) {
              setCurrentLine({ pt1: data.tripwire.pt1, pt2: data.tripwire.pt2 });
              if (data.tripwire.d_threshold) {
                setDThreshold(data.tripwire.d_threshold);
              }
            }
          } catch (e) {
            console.error('Telemetry parse error', e);
          }
        };

        socket.onclose = () => {
          setConnected(false);
          reconnectTimeout = setTimeout(connectWebSocket, 2000);
        };

        socket.onerror = () => {
          setConnected(false);
          socket.close();
        };
      } catch (err) {
        setConnected(false);
        reconnectTimeout = setTimeout(connectWebSocket, 2000);
      }
    };

    connectWebSocket();

    return () => {
      if (socket) socket.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [API_BASE, WS_URL, isDragging, fetchDevices]);

  // 2. Tripwire Canvas Render with DYNAMIC RESOLUTION
  const renderCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    if (!currentLine.pt1 || !currentLine.pt2) return;

    // Scale factors using dynamic native video resolution
    const sx = width / nativeW;
    const sy = height / nativeH;

    const x1 = currentLine.pt1[0] * sx;
    const y1 = currentLine.pt1[1] * sy;
    const x2 = currentLine.pt2[0] * sx;
    const y2 = currentLine.pt2[1] * sy;

    // Normal vector
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.max(1e-5, Math.hypot(dx, dy));
    const nx = -dy / len;
    const ny = dx / len;
    const scaledBuffer = dThreshold * sx;

    // Hysteresis Safe Zones (Whispered Translucent Lines)
    ctx.setLineDash([4, 6]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';

    // Buffer Out
    ctx.beginPath();
    ctx.moveTo(x1 + nx * scaledBuffer, y1 + ny * scaledBuffer);
    ctx.lineTo(x2 + nx * scaledBuffer, y2 + ny * scaledBuffer);
    ctx.stroke();

    // Buffer In
    ctx.beginPath();
    ctx.moveTo(x1 - nx * scaledBuffer, y1 - ny * scaledBuffer);
    ctx.lineTo(x2 - nx * scaledBuffer, y2 - ny * scaledBuffer);
    ctx.stroke();

    ctx.setLineDash([]); // Reset dash

    // Main Tripwire Line (Crisp Laser Silver / Platinum)
    ctx.beginPath();
    ctx.lineWidth = isCalibrating ? 3 : 2;
    ctx.strokeStyle = isCalibrating ? '#FFFFFF' : '#E2E8F0';
    ctx.shadowColor = 'rgba(255, 255, 255, 0.4)';
    ctx.shadowBlur = isCalibrating ? 12 : 6;
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.shadowBlur = 0; // Reset shadow

    // Ingress Direction Arrow
    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2;
    const arrowLen = scaledBuffer * 1.15;
    const ax = cx - nx * arrowLen;
    const ay = cy - ny * arrowLen;

    ctx.beginPath();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#FFFFFF';
    ctx.moveTo(cx, cy);
    ctx.lineTo(ax, ay);
    ctx.stroke();

    // Endpoints A & B
    const drawPoint = (x, y, label, isStart) => {
      ctx.beginPath();
      ctx.arc(x, y, isCalibrating ? 6 : 4, 0, Math.PI * 2);
      ctx.fillStyle = isStart ? '#F8FAFC' : '#94A3B8';
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = '#090A0C';
      ctx.stroke();

      if (isCalibrating) {
        ctx.font = '10px Inter, sans-serif';
        ctx.fillStyle = '#F8FAFC';
        ctx.fillText(label, x + 8, y - 8);
      }
    };

    drawPoint(x1, y1, `A (${Math.round(currentLine.pt1[0])}, ${Math.round(currentLine.pt1[1])})`, true);
    drawPoint(x2, y2, `B (${Math.round(currentLine.pt2[0])}, ${Math.round(currentLine.pt2[1])})`, false);
  }, [currentLine, dThreshold, isCalibrating, nativeW, nativeH]);

  useEffect(() => {
    renderCanvas();
  }, [renderCanvas]);

  // Adjust canvas size to parent viewport
  useEffect(() => {
    const handleResize = () => {
      if (viewportRef.current && canvasRef.current) {
        canvasRef.current.width = viewportRef.current.clientWidth;
        canvasRef.current.height = viewportRef.current.clientHeight;
        renderCanvas();
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [renderCanvas]);

  // 3. Pointer Drag Interaction for Tripwire Calibration (Dynamic Normalization)
  const getNormalizedCoords = (clientX, clientY) => {
    if (!canvasRef.current) return [0, 0];
    const rect = canvasRef.current.getBoundingClientRect();
    const nx = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    const ny = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
    return [Math.round(nx * nativeW), Math.round(ny * nativeH)];
  };

  const handlePointerDown = (e) => {
    if (!isCalibrating || !canvasRef.current) return;
    e.preventDefault();
    e.stopPropagation();

    const startPt = getNormalizedCoords(e.clientX, e.clientY);
    dragStartRef.current = startPt;
    isDraggingRef.current = true;
    lastEditTimeRef.current = Date.now();
    setIsDragging(true);

    const onPointerMove = (moveEvt) => {
      if (!isDraggingRef.current || !dragStartRef.current) return;
      moveEvt.preventDefault();
      lastEditTimeRef.current = Date.now();
      const currentPt = getNormalizedCoords(moveEvt.clientX, moveEvt.clientY);
      setCurrentLine({ pt1: dragStartRef.current, pt2: currentPt });
    };

    const onPointerUp = (upEvt) => {
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);

      if (!isDraggingRef.current || !dragStartRef.current) {
        isDraggingRef.current = false;
        setIsDragging(false);
        return;
      }

      const endPt = getNormalizedCoords(upEvt.clientX, upEvt.clientY);
      isDraggingRef.current = false;
      setIsDragging(false);
      lastEditTimeRef.current = Date.now();

      const dist = Math.hypot(endPt[0] - dragStartRef.current[0], endPt[1] - dragStartRef.current[1]);
      if (dist >= 10) {
        const finalLine = { pt1: dragStartRef.current, pt2: endPt };
        setCurrentLine(finalLine);
        saveTripwire(finalLine.pt1, finalLine.pt2, dThreshold);
      }
      dragStartRef.current = null;
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);
  };

  // 4. Save Tripwire to Backend
  const saveTripwire = async (pt1, pt2, thresh) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/config/tripwire`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pt1: [Math.round(pt1[0]), Math.round(pt1[1])],
          pt2: [Math.round(pt2[0]), Math.round(pt2[1])],
          d_threshold: thresh
        })
      });
      if (res.ok) {
        triggerToast(`Tripwire Calibrated: A(${pt1[0]}, ${pt1[1]}) → B(${pt2[0]}, ${pt2[1]})`);
      }
    } catch (e) {
      triggerToast('Calibration save failed');
    }
  };

  // 5. Reset Counters
  const handleResetCounters = async () => {
    try {
      await fetch(`${API_BASE}/api/v1/reset`, { method: 'POST' });
      triggerToast('Occupancy counters and tracking state reset');
    } catch (e) {
      triggerToast('Reset request failed');
    }
  };

  // 6. Export CSV
  const handleExportCSV = () => {
    if (!stats.events || stats.events.length === 0) {
      triggerToast('No transit events recorded yet');
      return;
    }

    const headers = ['Timestamp', 'Object_ID', 'Event_Type', 'Direction', 'Inside_Occupancy'];
    const rows = stats.events.map((evt) => [
      evt.timestamp,
      evt.object_id,
      evt.type,
      evt.action,
      evt.inside
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `humancheck_audit_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    triggerToast('Event audit log exported to CSV');
  };

  const isCameraOffline = stats.camera_status === 'offline' || streamError;

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            top: 24,
            right: 24,
            zIndex: 9999,
            background: 'rgba(16, 18, 22, 0.95)',
            border: '1px solid var(--border-accent)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 18px',
            color: 'var(--text-primary)',
            fontSize: 13,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            backdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.6)'
          }}
        >
          <Check size={16} color="#E2E8F0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Modal Nhập RTSP Stream URL */}
      {showRtspModal && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <div className="modal-title">
                <Globe size={18} color="#E2E8F0" />
                <span>Kết Nối IP Camera (RTSP / HTTP)</span>
              </div>
              <button
                className="btn btn-secondary btn-icon-only"
                onClick={() => setShowRtspModal(false)}
              >
                <X size={15} />
              </button>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Nhập đường dẫn luồng video IP Camera trực tiếp của doanh nghiệp hoặc camera an ninh:
            </p>
            <form onSubmit={handleConnectRtsp}>
              <input
                type="text"
                placeholder="rtsp://admin:password@192.168.1.100:554/stream1"
                value={rtspInput}
                onChange={(e) => setRtspInput(e.target.value)}
                className="modal-input"
                autoFocus
              />
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowRtspModal(false)}
                >
                  Hủy
                </button>
                <button type="submit" className="btn btn-primary">
                  Kết Nối
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Top Navigation Bar */}
      <header className="header">
        <div className="brand-section">
          <div className="brand-icon-wrapper">
            <Shield size={20} />
          </div>
          <div className="brand-titles">
            <span className="brand-name">HumanCheck</span>
            <span className="brand-tag">Swiss DIP Surveillance Suite</span>
          </div>
        </div>

        {/* Device Selector & Quick Hardware Scan */}
        <div className="device-selector-group">
          <Camera size={14} color="#94A3B8" />
          <select
            className="device-select"
            value={activeSource}
            onChange={(e) => handleSwitchSource(e.target.value)}
            title="Chọn camera hoặc nguồn video giám sát"
          >
            {devices.map((dev) => (
              <option key={String(dev.id)} value={String(dev.id)}>
                {dev.type === 'webcam' ? '📹 ' : dev.type === 'rtsp' ? '🌐 ' : '📁 '}
                {dev.name} ({dev.resolution ? `${dev.resolution[0]}x${dev.resolution[1]}` : ''})
              </option>
            ))}
            <option value="CUSTOM_RTSP">🌐 + Nhập địa chỉ IP Camera (RTSP)...</option>
          </select>

          <button
            className="btn btn-secondary btn-icon-only"
            style={{ width: 26, height: 26, padding: 0 }}
            onClick={handleScanDevices}
            disabled={isScanning}
            title="Quét lại cổng thiết bị camera USB"
          >
            <RefreshCw size={12} className={isScanning ? 'spin' : ''} />
          </button>
        </div>

        <div className="header-status-group">
          <div className="status-pill">
            <span className={isPaused ? 'status-dot-paused' : 'status-dot'}></span>
            <span>{isPaused ? 'Engine Paused' : 'Live Core Engine'}</span>
          </div>

          <div className="status-pill">
            <Activity size={14} color="#94A3B8" />
            <span className="font-mono">{stats.fps.toFixed(1)} FPS</span>
          </div>

          <div className="status-pill">
            {stats.is_night_mode ? (
              <Moon size={14} color="#94A3B8" />
            ) : (
              <Sun size={14} color="#94A3B8" />
            )}
            <span>{stats.is_night_mode ? 'CLAHE Adaptive' : 'Standard Illumination'}</span>
          </div>

          <div className="status-pill">
            {connected && !isCameraOffline ? (
              <Wifi size={14} color="#10B981" />
            ) : (
              <WifiOff size={14} color="#EF4444" />
            )}
            <span>
              {isCameraOffline
                ? 'Camera Offline'
                : connected
                ? 'Sync Online'
                : 'Connecting'}
            </span>
          </div>
        </div>

        <div className="header-actions">
          <button
            className={`btn ${isPaused ? 'btn-primary' : 'btn-secondary'}`}
            onClick={handleTogglePlayback}
            title={isPaused ? "Resume video stream" : "Pause video stream"}
          >
            {isPaused ? <Play size={15} /> : <Pause size={15} />}
            <span>{isPaused ? 'Start Stream' : 'Pause Stream'}</span>
          </button>

          <button
            className={`btn ${isCalibrating ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setIsCalibrating(!isCalibrating)}
            title="Calibrate virtual tripwire directly on the video viewport"
          >
            <Crosshair size={15} />
            <span>{isCalibrating ? 'Exit Calibration' : 'Calibrate Line'}</span>
          </button>

          <button
            className="btn btn-secondary"
            onClick={handleResetCounters}
            title="Reset occupancy counters and centroid tracks"
          >
            <RotateCcw size={15} />
            <span>Reset</span>
          </button>

          <button
            className="btn btn-secondary btn-icon-only"
            onClick={() => setShowConfigDrawer(!showConfigDrawer)}
            title="Tripwire Settings & Hysteresis Tuning"
          >
            <Sliders size={15} />
          </button>
        </div>
      </header>

      {/* Key Metric KPI Cards */}
      <section className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Interior Occupancy</span>
            <div className="metric-icon-box">
              <Users size={16} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{stats.inside}</span>
            <span className="metric-unit">Active Guests</span>
          </div>
          <div className="metric-footer">
            <Shield size={12} />
            <span>Verified by Hysteresis State Machine</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Total Ingress</span>
            <div className="metric-icon-box">
              <UserPlus size={16} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{stats.count_in}</span>
            <span className="metric-unit">Entries</span>
          </div>
          <div className="metric-footer">
            <ArrowDownRight size={12} />
            <span>Threshold Gate Ingress</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Total Egress</span>
            <div className="metric-icon-box">
              <UserMinus size={16} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{stats.count_out}</span>
            <span className="metric-unit">Exits</span>
          </div>
          <div className="metric-footer">
            <ArrowUpRight size={12} />
            <span>Verified Perimeter Departures</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Pure DIP Throughput</span>
            <div className="metric-icon-box">
              <Gauge size={16} />
            </div>
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{stats.fps.toFixed(1)}</span>
            <span className="metric-unit">Frames / Sec</span>
          </div>
          <div className="metric-footer">
            <Activity size={12} />
            <span>{nativeW}×{nativeH}px Processing Canvas</span>
          </div>
        </div>
      </section>

      {/* Configuration Drawer when toggled */}
      {showConfigDrawer && (
        <section
          className="panel"
          style={{ marginBottom: 'var(--space-lg)', border: '1px solid var(--border-accent)' }}
        >
          <div className="panel-header">
            <div className="panel-title-group">
              <Sliders size={14} color="#94A3B8" />
              <span className="panel-title">Precision Hysteresis & Tripwire Geometry</span>
            </div>
            <button
              className="btn btn-secondary btn-icon-only"
              onClick={() => setShowConfigDrawer(false)}
            >
              <Check size={14} />
            </button>
          </div>
          <div
            className="config-group"
            style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}
          >
            <div className="config-item">
              <div className="config-label-row">
                <span>Safe Zone Buffer (d_threshold)</span>
                <span>{dThreshold} px</span>
              </div>
              <input
                type="range"
                min="10"
                max="80"
                step="5"
                value={dThreshold}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setDThreshold(val);
                  saveTripwire(currentLine.pt1, currentLine.pt2, val);
                }}
                className="slider-input"
              />
            </div>

            <div className="config-item">
              <div className="config-label-row">
                <span>Vector Origin Point A (X1, Y1)</span>
                <span>
                  {currentLine.pt1[0]}, {currentLine.pt1[1]}
                </span>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Drag anywhere across the camera viewport to re-anchor Point A.
              </span>
            </div>

            <div className="config-item">
              <div className="config-label-row">
                <span>Vector Terminal Point B (X2, Y2)</span>
                <span>
                  {currentLine.pt2[0]}, {currentLine.pt2[1]}
                </span>
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Release mouse to instantly commit geometric coordinates.
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Primary Workspace Grid: Surveillance Viewport & Event Audit Log */}
      <main className="workspace-grid">
        {/* Main Surveillance Viewport */}
        <div className="panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <Camera size={15} color="#E2E8F0" />
              <span className="panel-title">
                {activeTab === 'video'
                  ? 'Spatial Tracking & HUD Viewport'
                  : 'Module 3 Foreground Mask Viewport'}
              </span>
              <span className="panel-badge">
                {isCalibrating ? 'Drag Mouse to Draw Tripwire' : `${nativeW}×${nativeH} Stream`}
              </span>
            </div>

            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <button
                className={`btn ${isPaused ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '4px 10px', fontSize: 11 }}
                onClick={handleTogglePlayback}
                title={isPaused ? "Resume video processing" : "Pause video processing"}
              >
                {isPaused ? <Play size={12} /> : <Pause size={12} />}
                <span>{isPaused ? 'Resume' : 'Pause'}</span>
              </button>

              <button
                className={`btn btn-icon-only ${activeTab === 'video' ? 'btn-active' : 'btn-secondary'}`}
                onClick={() => setActiveTab('video')}
                title="View annotated spatial tracking feed"
              >
                <Camera size={14} />
              </button>
              <button
                className={`btn btn-icon-only ${activeTab === 'mask' ? 'btn-active' : 'btn-secondary'}`}
                onClick={() => setActiveTab('mask')}
                title="View clean foreground segmentation mask"
              >
                <Layers size={14} />
              </button>
            </div>
          </div>

          <div className="viewport-container" ref={viewportRef}>
            {/* Live Video Feed Image */}
            <img
              key={streamKey}
              src={
                activeTab === 'video'
                  ? `${API_BASE}/api/v1/stream/video?t=${streamKey}`
                  : `${API_BASE}/api/v1/stream/mask?t=${streamKey}`
              }
              alt="Surveillance Video Feed"
              className="viewport-stream"
              onError={() => setStreamError(true)}
              onLoad={() => setStreamError(false)}
            />

            {/* Offline Backdrop with VideoOff & Retry Action */}
            {isCameraOffline && (
              <div className="offline-backdrop">
                <div className="offline-icon-box">
                  <VideoOff size={26} />
                </div>
                <div className="offline-title">Tín hiệu Camera bị gián đoạn</div>
                <div className="offline-subtitle">
                  Thiết bị camera hoặc nguồn stream hiện không khả dụng. Hệ thống đang tự động thử lại kết nối...
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleRetryStream}
                  style={{ marginTop: 6 }}
                >
                  <RefreshCw size={14} />
                  <span>Thử lại ngay</span>
                </button>
              </div>
            )}

            {/* Stream Paused Badge */}
            {isPaused && (
              <div
                style={{
                  position: 'absolute',
                  top: 14,
                  right: 14,
                  background: 'rgba(16, 18, 22, 0.90)',
                  border: '1px solid var(--border-accent)',
                  borderRadius: 'var(--radius-full)',
                  padding: '4px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  color: 'var(--text-primary)',
                  backdropFilter: 'blur(16px)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
                  zIndex: 15
                }}
              >
                <Pause size={12} color="#E2E8F0" />
                <span>Stream Paused</span>
              </div>
            )}

            {/* Interactive Canvas Overlay for Tripwire */}
            <canvas
              ref={canvasRef}
              className="overlay-canvas"
              onPointerDown={handlePointerDown}
              style={{
                pointerEvents: isCalibrating ? 'auto' : 'none',
                cursor: isCalibrating ? (isDragging ? 'grabbing' : 'crosshair') : 'default'
              }}
            />

            {/* Bottom HUD Bar */}
            <div className="viewport-overlay-controls">
              <div className="viewport-hud-info">
                <div className="hud-item">
                  <span>Tripwire Gate:</span>
                  <strong>
                    A({currentLine.pt1[0]}, {currentLine.pt1[1]}) → B({currentLine.pt2[0]},{' '}
                    {currentLine.pt2[1]})
                  </strong>
                </div>
                <div className="hud-item">
                  <span>Buffer:</span>
                  <strong>±{dThreshold}px</strong>
                </div>
                <div className="hud-item">
                  <span>Tracked Targets:</span>
                  <strong>{stats.active_objects_count}</strong>
                </div>
              </div>

              <div>
                {isCalibrating && (
                  <span
                    style={{
                      fontSize: 11,
                      color: 'var(--text-primary)',
                      letterSpacing: '0.04em',
                      textTransform: 'uppercase'
                    }}
                  >
                    Click & Drag on Frame to Redefine Line
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Secondary Column: Auxiliary Feed & Transit Event Stream */}
        <div className="secondary-feeds">
          {/* Auxiliary Feed: Clean Mask Preview when main is video */}
          <div className="mini-viewport-card">
            <div className="mini-viewport-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Layers size={13} />
                <span>Clean Mask Telemetry (Module 3)</span>
              </div>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>MOG2 Pure DIP</span>
            </div>
            <div className="mini-viewport-content">
              <img
                src={`${API_BASE}/api/v1/stream/mask?t=${streamKey}`}
                alt="Foreground Mask"
                className="mini-viewport-stream"
              />
            </div>
          </div>

          {/* Real-time Transit Audit Log */}
          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-header">
              <div className="panel-title-group">
                <Activity size={14} color="#94A3B8" />
                <span className="panel-title">Transit Audit Log</span>
              </div>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: 11 }}
                onClick={handleExportCSV}
                title="Download CSV Audit Record"
              >
                <Download size={13} />
                <span>Export CSV</span>
              </button>
            </div>

            <div className="event-table-container">
              {stats.events && stats.events.length > 0 ? (
                <table className="event-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Object</th>
                      <th>Direction</th>
                      <th>Interior</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.events.map((evt) => (
                      <tr key={evt.id}>
                        <td className="font-mono">{evt.timestamp}</td>
                        <td className="font-mono">#{evt.object_id}</td>
                        <td>
                          <span
                            className={`badge-direction ${
                              evt.type === 'IN' ? 'badge-in' : 'badge-out'
                            }`}
                          >
                            {evt.type === 'IN' ? (
                              <ArrowDownRight size={11} />
                            ) : (
                              <ArrowUpRight size={11} />
                            )}
                            {evt.action}
                          </span>
                        </td>
                        <td className="font-mono">{evt.inside}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty-state">
                  <Activity size={24} className="empty-state-icon" />
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Awaiting perimeter transit events...
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                    Tripwire crossings will be logged in real-time.
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

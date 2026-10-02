const $ = (selector) => document.querySelector(selector);
const time = (value) => new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value));
const title = (value) => String(value).replaceAll('-', ' ').replace(/\b\w/g, (character) => character.toUpperCase());

let selectedCamera = null;

function connectCameraStream(camera) {
  const image = $('#camera-feed');
  if (!camera) {
    image.removeAttribute('src');
    $('#camera-title').textContent = 'No live camera selected';
    $('#stream-status').textContent = 'offline';
    $('#camera-placeholder').hidden = false;
    return;
  }
  selectedCamera = camera;
  $('#camera-title').textContent = `${camera.name} · ${camera.location}`;
  $('#stream-status').textContent = camera.status;
  $('#camera-placeholder').hidden = false;
  image.onload = () => { $('#camera-placeholder').hidden = true; $('#stream-status').textContent = 'live'; };
  image.onerror = () => { $('#camera-placeholder').hidden = false; $('#stream-status').textContent = 'waiting'; setTimeout(() => connectCameraStream(camera), 3000); };
  image.src = `/api/cameras/${encodeURIComponent(camera.id)}/stream?ts=${Date.now()}`;
}

function renderCameras(cameras) {
  const live = cameras.filter(camera => camera.status === 'online');
  $('#cameras').textContent = live.length;
  $('#camera-count').textContent = `${cameras.length} configured`;
  $('#camera-caption').textContent = 'verified worker heartbeats';
  $('#floorplan').innerHTML = cameras.length
    ? cameras.map((camera, index) => `<div class="map-camera" style="left:${10 + (index * 27) % 75}%;top:${22 + (index * 31) % 55}%"><span></span><strong>${camera.name}</strong><small>${camera.location}</small><em>${camera.status}</em></div>`).join('')
    : '<div class="map-empty">No physical camera topology is configured yet.</div>';
  if (!selectedCamera || !cameras.some(camera => camera.id === selectedCamera.id)) {
    connectCameraStream(live[0] || null);
  } else {
    const current = cameras.find(camera => camera.id === selectedCamera.id);
    if (current.status !== selectedCamera.status) connectCameraStream(current);
  }
}

async function load() {
  try {
    const [overview, tracks, cameras] = await Promise.all([
      fetch('/api/overview').then(r => r.json()),
      fetch('/api/tracks').then(r => r.json()),
      fetch('/api/cameras').then(r => r.json())
    ]);
    const demo = overview.mode === 'demo';
    $('#mode-label').textContent = demo ? 'DEMO MODE' : 'LIVE MODE';
    $('#mode-notice').innerHTML = demo
      ? '<strong>DEMO DATA:</strong> camera locations, tracks, and observations are synthetic. No physical cameras are connected.'
      : '<strong>LIVE MODE:</strong> only cameras with a recent authenticated worker heartbeat count as online.';
    $('#active').textContent = overview.active_tracks;
    $('#lost').textContent = overview.lost_tracks;
    $('#exited').textContent = overview.exited_tracks;
    renderCameras(cameras);
    $('#track-list').innerHTML = tracks.map(track => `<tr data-track="${track.id}"><td><strong>${track.id}</strong></td><td><span class="state ${track.state}">${track.state}</span></td><td>${title(track.current_camera_id || '—')}</td><td>${title(track.current_zone_id || '—')}</td><td>${Math.round(track.confidence * 100)}%</td><td>${track.observation_count}</td></tr>`).join('');
    document.querySelectorAll('[data-track]').forEach(row => row.addEventListener('click', () => showTrack(row.dataset.track)));
    if (tracks.length) showTrack(tracks[0].id);
  } catch (error) {
    $('#mode-notice').textContent = `Dashboard data error: ${error.message}`;
  }
}

async function showTrack(id) {
  const [trackResponse, candidateResponse] = await Promise.all([
    fetch(`/api/tracks/${encodeURIComponent(id)}`, {headers: {'X-Operator': 'dashboard-demo'}}),
    fetch(`/api/tracks/${encodeURIComponent(id)}/continuity-candidates`, {headers: {'X-Operator': 'dashboard-demo'}})
  ]);
  if (!trackResponse.ok) return;
  const track = await trackResponse.json();
  const candidates = candidateResponse.ok ? await candidateResponse.json() : [];
  const last = track.observations.at(-1);
  if (!last) return;
  $('#track-title').textContent = track.id;
  $('#track-state').textContent = track.state;
  $('#track-state').className = `pill ${track.state}`;
  $('#track-location').textContent = `${title(last.zone_id)} · ${title(last.camera_id)}`;
  $('#track-time').textContent = `Seen ${time(last.observed_at)} · ${Math.round(last.confidence * 100)}% detection confidence`;
  $('#timeline').innerHTML = track.observations.slice().reverse().map(observation => `<li><span></span><div><strong>${title(observation.zone_id)}</strong><p>${title(observation.camera_id)} · ${time(observation.observed_at)} · quality ${Math.round(observation.quality * 100)}%</p></div></li>`).join('');
  $('#continuity-list').innerHTML = candidates.length ? candidates.map(candidate => `<article class="candidate ${candidate.tier}"><div><strong>${candidate.track_id}</strong><p>${title(candidate.route)} · ${candidate.elapsed_seconds}s</p></div><span>${Math.round(candidate.score * 100)}% · ${candidate.tier}</span></article>`).join('') : '<p class="hint">No topology-valid predecessor is available.</p>';
  $('#track-empty').hidden = true;
  $('#track-details').hidden = false;
}

$('#refresh').addEventListener('click', load);
load();
setInterval(load, 5000);

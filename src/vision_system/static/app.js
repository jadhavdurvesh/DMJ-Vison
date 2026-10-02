const $ = (selector) => document.querySelector(selector);
const time = (value) => new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value));
const title = (value) => value.replaceAll('-', ' ').replace(/\b\w/g, (character) => character.toUpperCase());

function connectCameraStream() {
  const image = $('#camera-feed');
  image.src = '/api/cameras/north-entry/stream';
  image.onload = () => { $('#camera-placeholder').hidden = true; $('#stream-status').textContent = 'live'; };
  image.onerror = () => { $('#camera-placeholder').hidden = false; $('#stream-status').textContent = 'waiting for worker'; setTimeout(connectCameraStream, 3000); };
}

async function load() {
  const [overview, tracks] = await Promise.all([fetch('/api/overview').then(r => r.json()), fetch('/api/tracks').then(r => r.json())]);
  $('#active').textContent = overview.active_tracks;
  $('#lost').textContent = overview.lost_tracks;
  $('#exited').textContent = overview.exited_tracks;
  $('#cameras').textContent = overview.camera_count;
  $('#track-list').innerHTML = tracks.map(track => `<tr data-track="${track.id}"><td><strong>${track.id}</strong></td><td><span class="state ${track.state}">${track.state}</span></td><td>${title(track.current_camera_id || '—')}</td><td>${title(track.current_zone_id || '—')}</td><td>${Math.round(track.confidence * 100)}%</td><td>${track.observation_count}</td></tr>`).join('');
  document.querySelectorAll('[data-track]').forEach(row => row.addEventListener('click', () => showTrack(row.dataset.track)));
  if (tracks.length) showTrack(tracks[0].id);
}
async function showTrack(id) {
  const [track, candidates] = await Promise.all([fetch(`/api/tracks/${id}`, {headers: {'X-Operator': 'dashboard-demo'}}).then(r => r.json()), fetch(`/api/tracks/${id}/continuity-candidates`, {headers: {'X-Operator': 'dashboard-demo'}}).then(r => r.json())]);
  const last = track.observations.at(-1);
  $('#track-title').textContent = track.id;
  $('#track-state').textContent = track.state;
  $('#track-state').className = `pill ${track.state}`;
  $('#track-location').textContent = `${title(last.zone_id)} · ${title(last.camera_id)}`;
  $('#track-time').textContent = `Seen ${time(last.observed_at)} · ${Math.round(last.confidence * 100)}% association confidence`;
  $('#timeline').innerHTML = track.observations.slice().reverse().map(observation => `<li><span></span><div><strong>${title(observation.zone_id)}</strong><p>${title(observation.camera_id)} · ${time(observation.observed_at)} · quality ${Math.round(observation.quality * 100)}%</p></div></li>`).join('');
  $('#continuity-list').innerHTML = candidates.length ? candidates.map(candidate => `<article class="candidate ${candidate.tier}"><div><strong>${candidate.track_id}</strong><p>${title(candidate.route)} · ${candidate.elapsed_seconds}s</p></div><span>${Math.round(candidate.score * 100)}% · ${candidate.tier}</span></article>`).join('') : '<p class="hint">No topology-valid predecessor is available.</p>';
  $('#track-empty').hidden = true; $('#track-details').hidden = false;
}
$('#refresh').addEventListener('click', load); load(); connectCameraStream(); setInterval(load, 5000);

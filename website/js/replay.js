function monitorHLSStream() {
    if (!hls) return;
    
    setInterval(() => {
        const stats = hls.stats;
        const health = {
            buffered: stats.buffered,
            latency: stats.latency,
            droppedFrames: stats.droppedFrames,
            bitrate: stats.bitrate
        };
        
        // Update UI with stream health
        updateStreamHealth(health);
        
        // Log issues if stream is unhealthy
        if (stats.droppedFrames > 30) {
            console.warn('HLS Stream: High dropped frames', stats);
        }
    }, 5000);
}

function updateStreamHealth(health) {
    $('#stream-health').html(`
        <div>Buffer: ${Math.round(health.buffered)}s</div>
        <div>Latency: ${Math.round(health.latency)}ms</div>
        <div>Bitrate: ${Math.round(health.bitrate/1024)}kbps</div>
    `);
}
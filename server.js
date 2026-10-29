const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const { bundle } = require('@remotion/bundler');
const { renderMedia, selectComposition } = require('@remotion/renderer');

const app = express();
const PORT = 3000;

app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/out', express.static(path.join(__dirname, 'out')));

// Ensure directories
const videosDir = path.join(__dirname, 'public', 'videos');
const outDir = path.join(__dirname, 'out');
fs.mkdirSync(videosDir, { recursive: true });
fs.mkdirSync(outDir, { recursive: true });

// Multer for video uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, videosDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    const basename = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9_-]/g, '_');
    cb(null, `${basename}_${Date.now()}${ext}`);
  },
});
const upload = multer({ storage });

// API: List available videos
app.get('/api/videos', (req, res) => {
  try {
    const files = fs.readdirSync(videosDir).filter(f => f.match(/\.(mp4|mov|webm)$/i));
    res.json({ success: true, videos: files });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// API: Upload video
app.post('/api/upload', upload.single('video'), (req, res) => {
  if (!req.file) return res.status(400).json({ success: false, error: 'No file uploaded' });
  res.json({
    success: true,
    filename: req.file.filename,
    path: `videos/${req.file.filename}`,
  });
});

// Rendering state
let currentRender = {
  status: 'idle', // 'idle' | 'rendering' | 'done' | 'error'
  progress: 0,
  outputFile: null,
  error: null,
};

app.get('/api/render-status', (req, res) => {
  res.json(currentRender);
});

// API: Start Render
app.post('/api/render', async (req, res) => {
  if (currentRender.status === 'rendering') {
    return res.status(400).json({ success: false, error: 'Render already in progress' });
  }

  const inputProps = req.body;
  const outFileName = `compare_${Date.now()}.mp4`;
  const outputPath = path.join(outDir, outFileName);

  currentRender = {
    status: 'rendering',
    progress: 0,
    outputFile: null,
    error: null,
  };

  res.json({ success: true, message: 'Rendering started' });

  try {
    console.log('[Server] Bundling Remotion project...');
    const bundled = await bundle({
      entryPoint: path.join(__dirname, 'src', 'index.ts'),
      webpackOverride: (config) => config,
    });

    console.log('[Server] Selecting composition...');
    const composition = await selectComposition({
      serveUrl: bundled,
      id: 'CompareVideo',
      inputProps,
    });

    console.log('[Server] Rendering media...');
    await renderMedia({
      composition,
      serveUrl: bundled,
      codec: 'h264',
      outputLocation: outputPath,
      inputProps,
      onProgress: ({ progress }) => {
        currentRender.progress = Math.round(progress * 100);
        console.log(`[Render] Progress: ${currentRender.progress}%`);
      },
    });

    console.log('[Server] Render finished:', outputPath);
    currentRender = {
      status: 'done',
      progress: 100,
      outputFile: `/out/${outFileName}`,
      error: null,
    };
  } catch (err) {
    console.error('[Server] Render error:', err);
    currentRender = {
      status: 'error',
      progress: 0,
      outputFile: null,
      error: err.message,
    };
  }
});

app.listen(PORT, () => {
  console.log(`===============================================`);
  console.log(` TikTok Compare Video Studio is running!`);
  console.log(` URL: http://localhost:${PORT}`);
  console.log(`===============================================`);
});

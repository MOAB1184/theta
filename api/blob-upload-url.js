import { put } from '@vercel/blob';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  try {
    // Debug: log the raw body
    console.log('RAW req.body:', req.body);
    const body = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    console.log('PARSED body:', body);
    const { filename, contentType, class_id } = body;
    if (!filename || !contentType || !class_id) {
      console.log('Missing required fields:', { filename, contentType, class_id });
      return res.status(400).json({ error: 'Missing required fields' });
    }
    const pathname = `recordings/${class_id}/${filename}`;
    console.log('Calling put with:', { pathname, contentType });
    const { url, blob } = await put(pathname, {
      access: 'public',
      contentType,
    });
    console.log('put result:', { url, blob });
    return res.status(200).json({ uploadUrl: url, blobUrl: blob.url });
  } catch (err) {
    console.error('ERROR in /api/blob-upload-url:', err);
    return res.status(500).json({ error: 'Failed to generate upload URL', details: err.message });
  }
} 
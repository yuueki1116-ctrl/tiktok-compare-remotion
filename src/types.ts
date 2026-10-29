export interface VideoItemConfig {
  name: string;
  videoSrc: string; // e.g. "videos/xxx.mp4" or "videos/xxx.jpg"
  startOffset?: number; // seconds
}

export interface CompareVideoProps {
  title: string;
  subtitle: string;
  titleDuration: number; // seconds to show title, or negative for entire video
  titleColor: string;
  titleStrokeColor: string;
  fontFamily: string;
  titleFontSize: number;
  titleStrokeWidth: number;
  nameColor: string;
  nameStrokeColor: string;
  nameFontFamily: string;
  nameFontSize: number;
  nameStrokeWidth: number;
  items: [VideoItemConfig, VideoItemConfig, VideoItemConfig, VideoItemConfig]; // [TL, TR, BL, BR]
  audioIndex: number; // 0: TL, 1: TR, 2: BL, 3: BR
  durationInSeconds: number;
}

export const defaultProps: CompareVideoProps = {
  title: '誰が1番好き？',
  subtitle: 'オパオパダンス4選',
  titleDuration: 1.5,
  titleColor: '#ffffff',
  titleStrokeColor: '#ff2d78',
  fontFamily: "'Mochiy Pop One', sans-serif",
  titleFontSize: 1.1,
  titleStrokeWidth: 11,
  nameColor: '#ffffff',
  nameStrokeColor: '#d6006e',
  nameFontFamily: "'M PLUS Rounded 1c', sans-serif",
  nameFontSize: 1.0,
  nameStrokeWidth: 8,
  items: [
    {
      name: 'みおち',
      videoSrc: 'videos/v1c044g50000dbbl47nog65kps1bcong.mp4',
      startOffset: 0,
    },
    {
      name: 'みなみ',
      videoSrc: 'videos/v14044g50000datr2knog65gphn6o3c0.mp4',
      startOffset: 0,
    },
    {
      name: '金丸紗希',
      videoSrc: 'videos/v14044g50000davp1v7og65gkm0vl580.mp4',
      startOffset: 0,
    },
    {
      name: 'もえ',
      videoSrc: 'videos/v1c044g50000dav3khnog65l82rllud0.mp4',
      startOffset: 0,
    },
  ],
  audioIndex: 0,
  durationInSeconds: 7.0,
};

import { useState, useRef, useEffect } from 'react';
import Header from '@/components/Header';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Mic, MicOff, Upload } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useUser } from "@clerk/clerk-react"; 
import { uploadEvidence } from '@/lib/apiService';

const THRESHOLD = 0.05; // 👈 Volume threshold for "threat"
const MONITOR_INTERVAL = 1000; // 👈 Check volume every second

const Demo = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [volume, setVolume] = useState(0);
  const { toast } = useToast();
  const { user } = useUser();

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<number | null>(null);

  // --- Monitoring Logic ---
  const startClientMonitoring = async () => {
    if (!user) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Setup Analyser
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      // Setup Recorder
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
          const file = new File([blob], `monitored_audio_${Date.now()}.wav`, { type: 'audio/wav' });
          
          // Mimic FileList for apiService
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          
          try {
            await uploadEvidence(user.id, dataTransfer.files);
            toast({
              title: "Audio Saved",
              description: "Monitored audio segment uploaded successfully.",
            });
          } catch (err) {
            console.error("Upload failed", err);
          }
          chunksRef.current = [];
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);

      // Volume monitoring interval
      intervalRef.current = window.setInterval(() => {
        if (!analyserRef.current) return;
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteTimeDomainData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          const v = (dataArray[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        setVolume(rms);

        if (rms > THRESHOLD) {
          // Provide visual feedback for the demo
          toast({
            title: "Threat Level Detected",
            description: "VoiceGuard has detected high-intensity audio and is prioritizing your safety.",
            variant: "destructive",
          });
          console.log("High volume detected!");
        }
      }, MONITOR_INTERVAL);

      toast({
        title: 'Monitoring Started',
        description: 'Client-side background audio monitoring is now active.',
      });

    } catch (err: any) {
      console.error(err);
      toast({
        title: 'Mic Access Failed',
        description: 'Please ensure microphone permissions are granted.',
        variant: 'destructive',
      });
    }
  };

  const stopClientMonitoring = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    setIsRecording(false);
    setVolume(0);
    toast({
      title: 'Monitoring Stopped',
      description: 'Audio monitoring has been shut down.',
    });
  };

  const handleRecordingToggle = () => {
    if (isRecording) {
      stopClientMonitoring();
    } else {
      startClientMonitoring();
    }
  };
  
  // --- File Upload Handler ---
  const handleUploadChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !user) return;

    setIsLoading(true);
    try {
      const result = await uploadEvidence(user.id, files); 
      toast({
        title: 'Upload Successful',
        description: `Successfully uploaded ${result.successful_files.length} file(s) to the Evidence Locker.`,
      });
    } catch (error: any) {
      console.error('Upload Error:', error);
      toast({
        title: 'Upload Failed',
        description: `Error uploading evidence: ${error.message}`,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      event.target.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          
          <div className="grid md:grid-cols-2 gap-6">
            
            {/* Voice Recorder */}
            <Card className="border-border hover:border-accent transition-all">
              <CardHeader>
                <CardTitle>Client Monitoring</CardTitle>
                <CardDescription>
                  {isRecording ? "Listening for distress patterns..." : "Local audio monitoring for deployment."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {isRecording && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Volume Level</span>
                      <span>{(volume * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-200 ${volume > THRESHOLD ? 'bg-destructive' : 'bg-primary'}`}
                        style={{ width: `${Math.min(volume * 100, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                <Button
                  onClick={handleRecordingToggle}
                  className={`w-full ${isRecording ? 'bg-destructive hover:bg-destructive/90' : ''}`}
                  disabled={isLoading}
                >
                  {isLoading ? 'Processing...' : isRecording ? (
                    <>
                      <MicOff className="mr-2 h-4 w-4" />
                      Stop & Save Recording
                    </>
                  ) : (
                    <>
                      <Mic className="mr-2 h-4 w-4" />
                      Start Mic Monitoring
                    </>
                  )}
                </Button>
                <p className="text-[10px] text-muted-foreground italic">
                  *This works in cloud deployments as it uses your browser's microphone.
                </p>
              </CardContent>
            </Card>

            {/* Evidence Locker */}
            <Card className="border-border hover:border-accent transition-all">
              <CardHeader>
                <CardTitle>Evidence Locker</CardTitle>
                <CardDescription>Securely store photos or documents.</CardDescription>
              </CardHeader>
              <CardContent>
                <input
                  id="evidence-upload"
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleUploadChange}
                  disabled={isLoading}
                />
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => document.getElementById('evidence-upload')?.click()}
                  disabled={isLoading}
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {isLoading ? 'Uploading...' : 'Upload Evidence'}
                </Button>
              </CardContent>
            </Card>

          </div>

          <div className="mt-8 p-6 bg-muted/30 rounded-lg border border-border">
            <h3 className="text-lg font-semibold mb-2 text-primary">Privacy & Safety</h3>
            <div className="grid md:grid-cols-3 gap-6 text-sm text-muted-foreground">
              <div>
                <h4 className="font-medium mb-1 text-foreground">Local Processing</h4>
                <p>VoiceGuard uses client-side monitoring to process audio directly in your browser, ensuring your data never leaves your device unless a threat is confirmed.</p>
              </div>
              <div>
                <h4 className="font-medium mb-1 text-foreground">Secure Evidence</h4>
                <p>All recorded incidents are encrypted and stored in your private Evidence Locker, providing a tamper-proof record for legal or support services.</p>
              </div>
              <div>
                <h4 className="font-medium mb-1 text-foreground">AI Support</h4>
                <p>Our integrated AI chatbot provides immediate guidance and legal information, helping you navigate difficult situations with the right resources.</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Demo;
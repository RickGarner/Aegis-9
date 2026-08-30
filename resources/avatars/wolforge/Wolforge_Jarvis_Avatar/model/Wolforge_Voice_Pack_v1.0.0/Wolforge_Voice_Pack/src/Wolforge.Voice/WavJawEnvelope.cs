namespace Wolforge.Voice;

public readonly record struct JawFrame(TimeSpan Time, float Openness);

public static class WavJawEnvelope
{
    public static IReadOnlyList<JawFrame> ReadPcm16Mono(string wavPath, JawEnvelopeOptions options)
    {
        using var br = new BinaryReader(File.OpenRead(wavPath));
        if (new string(br.ReadChars(4)) != "RIFF") throw new InvalidDataException("Not a RIFF WAV.");
        br.ReadUInt32();
        if (new string(br.ReadChars(4)) != "WAVE") throw new InvalidDataException("Not a WAVE file.");
        ushort format = 0, channels = 0, bits = 0; uint sampleRate = 0; long dataAt = 0; uint dataLength = 0;
        while (br.BaseStream.Position + 8 <= br.BaseStream.Length)
        {
            var id = new string(br.ReadChars(4)); var length = br.ReadUInt32(); var next = br.BaseStream.Position + length + (length & 1);
            if (id == "fmt ") { format=br.ReadUInt16(); channels=br.ReadUInt16(); sampleRate=br.ReadUInt32(); br.ReadUInt32(); br.ReadUInt16(); bits=br.ReadUInt16(); }
            else if (id == "data") { dataAt=br.BaseStream.Position; dataLength=length; break; }
            br.BaseStream.Position = next;
        }
        if (format != 1 || channels != 1 || bits != 16 || dataAt == 0) throw new InvalidDataException("Expected mono PCM16 WAV.");
        br.BaseStream.Position=dataAt;
        int frameSamples=Math.Max(1,(int)(sampleRate*options.FrameMilliseconds/1000));
        int total=(int)Math.Min(dataLength/2,int.MaxValue); var result=new List<JawFrame>((total+frameSamples-1)/frameSamples);
        double smooth=0; int index=0;
        while (index<total)
        {
            int n=Math.Min(frameSamples,total-index); double sum=0;
            for(int i=0;i<n;i++){ double s=br.ReadInt16()/32768.0; sum+=s*s; }
            double db=20*Math.Log10(Math.Max(1e-9,Math.Sqrt(sum/n)));
            double raw=db<=options.OpenThresholdDb?0:Math.Clamp((db-options.OpenThresholdDb)/(options.MaximumDb-options.OpenThresholdDb),0,1);
            double factor=raw>smooth?options.Attack:options.Release; smooth += (raw-smooth)*factor;
            result.Add(new JawFrame(TimeSpan.FromSeconds((double)index/sampleRate),(float)smooth)); index+=n;
        }
        return result;
    }
}

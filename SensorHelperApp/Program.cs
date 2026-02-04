using System;
using System.IO;
using LibreHardwareMonitor.Hardware;

class SensorHelper
{
    static Computer computer;

    static void Main()
    {
        // Log errors to file for debugging
        string logPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "sensor_error.log");

        try
        {
            computer = new Computer
            {
                IsCpuEnabled = true,
                IsGpuEnabled = true
            };

            computer.Open();
            Console.WriteLine("{\"status\":\"ready\"}");
            Console.Out.Flush();
        }
        catch (Exception ex)
        {
            string errorMsg = ex.ToString();
            try { File.WriteAllText(logPath, errorMsg); } catch { }
            Console.WriteLine("{\"error\":\"" + ex.Message.Replace("\"", "'").Replace("\n", " ").Replace("\r", "") + "\"}");
            Console.Out.Flush();
            return;
        }

        string line;
        while ((line = Console.ReadLine()) != null)
        {
            if (line == "quit") break;
            if (line == "read")
            {
                try
                {
                    var result = ReadSensors();
                    Console.WriteLine(result);
                    Console.Out.Flush();
                }
                catch (Exception ex)
                {
                    Console.WriteLine("{\"error\":\"" + ex.Message.Replace("\"", "'") + "\"}");
                    Console.Out.Flush();
                }
            }
            else if (line == "debug")
            {
                try
                {
                    DumpSensors();
                }
                catch (Exception ex)
                {
                    Console.WriteLine("Error: " + ex.Message);
                    Console.Out.Flush();
                }
            }
            else if (line == "diag")
            {
                try
                {
                    RunDiagnostics(logPath);
                }
                catch (Exception ex)
                {
                    Console.WriteLine("Diag error: " + ex.Message);
                    Console.Out.Flush();
                }
            }
        }

        try { computer.Close(); } catch { }
    }

    static void DumpSensors()
    {
        Console.Out.Flush();
        foreach (var hardware in computer.Hardware)
        {
            hardware.Update();
            Console.WriteLine("[" + hardware.HardwareType + "] " + hardware.Name);
            Console.Out.Flush();

            foreach (var sensor in hardware.Sensors)
            {
                if (sensor.Value == null) continue;
                Console.WriteLine("  [" + sensor.SensorType + "] " + sensor.Name + " = " + sensor.Value);
                Console.Out.Flush();
            }

            foreach (var sub in hardware.SubHardware)
            {
                sub.Update();
                Console.WriteLine("  [SubHardware] " + sub.Name);
                Console.Out.Flush();
                foreach (var sensor in sub.Sensors)
                {
                    if (sensor.Value == null) continue;
                    Console.WriteLine("    [" + sensor.SensorType + "] " + sensor.Name + " = " + sensor.Value);
                    Console.Out.Flush();
                }
            }
        }
        Console.WriteLine("END");
        Console.Out.Flush();
    }

    static void RunDiagnostics(string logPath)
    {
        var diagLines = new System.Collections.Generic.List<string>();
        diagLines.Add("=== SensorHelper Diagnostics ===");
        diagLines.Add("Time: " + DateTime.Now.ToString());
        diagLines.Add("App Directory: " + AppDomain.CurrentDomain.BaseDirectory);
        diagLines.Add("");

        // Check for driver files
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string[] driverFiles = { "WinRing0x64.sys", "WinRing0x64.dll", "WinRing0.sys", "WinRing0.dll" };
        diagLines.Add("=== Driver Files ===");
        foreach (var df in driverFiles)
        {
            string path = Path.Combine(baseDir, df);
            diagLines.Add(df + ": " + (File.Exists(path) ? "FOUND" : "missing"));
        }
        diagLines.Add("");

        // List all hardware and sensors
        diagLines.Add("=== Hardware & Sensors ===");
        bool foundCpuTemp = false;
        bool foundCpuPower = false;
        bool foundGpuPower = false;

        foreach (var hardware in computer.Hardware)
        {
            hardware.Update();
            diagLines.Add("[" + hardware.HardwareType + "] " + hardware.Name);

            foreach (var sensor in hardware.Sensors)
            {
                string val = sensor.Value.HasValue ? sensor.Value.Value.ToString("F1") : "null";
                diagLines.Add("  [" + sensor.SensorType + "] " + sensor.Name + " = " + val);

                if (hardware.HardwareType.ToString().Contains("Cpu"))
                {
                    if (sensor.SensorType.ToString() == "Temperature") foundCpuTemp = true;
                    if (sensor.SensorType.ToString() == "Power") foundCpuPower = true;
                }
                if (hardware.HardwareType.ToString().Contains("Gpu"))
                {
                    if (sensor.SensorType.ToString() == "Power") foundGpuPower = true;
                }
            }

            foreach (var sub in hardware.SubHardware)
            {
                sub.Update();
                diagLines.Add("  [SubHardware] " + sub.Name);
                foreach (var sensor in sub.Sensors)
                {
                    string val = sensor.Value.HasValue ? sensor.Value.Value.ToString("F1") : "null";
                    diagLines.Add("    [" + sensor.SensorType + "] " + sensor.Name + " = " + val);

                    if (sensor.SensorType.ToString() == "Temperature") foundCpuTemp = true;
                    if (sensor.SensorType.ToString() == "Power") foundCpuPower = true;
                }
            }
        }

        diagLines.Add("");
        diagLines.Add("=== Summary ===");
        diagLines.Add("CPU Temperature sensors: " + (foundCpuTemp ? "YES" : "NO - driver may not be loaded"));
        diagLines.Add("CPU Power sensors: " + (foundCpuPower ? "YES" : "NO - driver may not be loaded"));
        diagLines.Add("GPU Power sensors: " + (foundGpuPower ? "YES" : "NO"));

        // Write to log file
        string diagPath = Path.Combine(baseDir, "sensor_diag.log");
        try
        {
            File.WriteAllLines(diagPath, diagLines);
            Console.WriteLine("Diagnostics written to: " + diagPath);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Failed to write diag: " + ex.Message);
        }

        // Also output to console
        foreach (var line in diagLines)
        {
            Console.WriteLine(line);
        }
        Console.WriteLine("END");
        Console.Out.Flush();
    }

    static bool IsDiscreteGpu(string name)
    {
        // Discrete GPU identifiers
        return name.Contains(" RX ") || name.Contains(" RTX ") || name.Contains(" GTX ") ||
               name.Contains("Radeon RX") || name.Contains("GeForce") ||
               name.Contains("9070") || name.Contains("9080") || name.Contains("7900") ||
               name.Contains("4090") || name.Contains("4080") || name.Contains("5090");
    }

    static string ReadSensors()
    {
        double cpuTemp = 0, cpuClock = 0, cpuPower = 0;
        double gpuTemp = 0, gpuPercent = 0, gpuClock = 0, gpuMemClock = 0, gpuMemPercent = 0, gpuPower = 0;
        double gpuEdgeTemp = 0;
        double cpuTempFallback = 0;  // Any CPU temp as fallback
        double cpuClockSum = 0;
        int cpuClockCount = 0;
        bool foundDiscreteGpu = false;

        foreach (var hardware in computer.Hardware)
        {
            hardware.Update();
            var hwType = hardware.HardwareType.ToString();
            var hwName = hardware.Name;

            foreach (var sensor in hardware.Sensors)
            {
                if (sensor.Value == null) continue;
                var name = sensor.Name;
                var stype = sensor.SensorType.ToString();
                var val = (double)sensor.Value.Value;

                if (hwType.Contains("Cpu"))
                {
                    if (stype == "Temperature")
                    {
                        // Priority: Tctl/Tdie/Package > CCD > Core > any
                        if ((name.Contains("Tctl") || name.Contains("Tdie") || name.Contains("Package")) && cpuTemp == 0)
                            cpuTemp = val;
                        else if (name.Contains("CCD") && cpuTemp == 0)
                            cpuTemp = val;
                        else if (name.Contains("Core") && cpuTemp == 0)
                            cpuTemp = val;
                        else if (cpuTempFallback == 0)
                            cpuTempFallback = val;
                    }
                    else if (stype == "Clock" && name.Contains("Core") && !name.Contains("Effective") && !name.Contains("Average"))
                    {
                        if (!double.IsNaN(val) && val > 0)
                        {
                            cpuClockSum += val;
                            cpuClockCount++;
                        }
                    }
                    else if (stype == "Power" && (name.Contains("Package") || name.Contains("CPU") || name.Contains("Power")))
                    {
                        if (cpuPower == 0)
                            cpuPower = val;
                    }
                }
                else if (hwType.Contains("Gpu"))
                {
                    // Skip integrated GPU if we already found a discrete GPU
                    bool isDiscrete = IsDiscreteGpu(hwName);


                    if (foundDiscreteGpu && !isDiscrete)
                        continue;

                    // If this is a discrete GPU and we previously had integrated, reset values
                    if (isDiscrete && !foundDiscreteGpu)
                    {
                        foundDiscreteGpu = true;
                        gpuTemp = 0;
                        gpuPercent = 0;
                        gpuClock = 0;
                        gpuMemClock = 0;
                        gpuMemPercent = 0;
                        gpuPower = 0;
                        gpuEdgeTemp = 0;
                    }

                    if (stype == "Temperature")
                    {
                        if (name.Contains("Hot Spot") || name.Contains("Junction"))
                            gpuTemp = val;
                        else if (name == "GPU Core" && gpuEdgeTemp == 0)
                            gpuEdgeTemp = val;
                        else if (gpuEdgeTemp == 0)
                            gpuEdgeTemp = val;
                    }
                    else if (stype == "Load")
                    {
                        if (name == "GPU Core" && gpuPercent == 0)
                            gpuPercent = val;
                        else if (name == "GPU Memory" && gpuMemPercent == 0)
                            gpuMemPercent = val;
                    }
                    else if (stype == "Clock")
                    {
                        if (name == "GPU Core" && gpuClock == 0)
                            gpuClock = val;
                        else if (name == "GPU Memory" && gpuMemClock == 0)
                            gpuMemClock = val;
                    }
                    else if (stype == "Power")
                    {
                        if ((name.Contains("Package") || name == "GPU Core") && gpuPower == 0)
                            gpuPower = val;
                    }
                }
            }

            // Check SubHardware (AMD CPUs often have sensors here)
            foreach (var sub in hardware.SubHardware)
            {
                sub.Update();
                foreach (var sensor in sub.Sensors)
                {
                    if (sensor.Value == null) continue;
                    var name = sensor.Name;
                    var stype = sensor.SensorType.ToString();
                    var val = (double)sensor.Value.Value;

                    if (stype == "Temperature")
                    {
                        if ((name.Contains("Tctl") || name.Contains("Tdie")) && cpuTemp == 0)
                            cpuTemp = val;
                        else if (name.Contains("CCD") && cpuTemp == 0)
                            cpuTemp = val;
                        else if (name.Contains("Core") && cpuTemp == 0)
                            cpuTemp = val;
                        else if (cpuTempFallback == 0)
                            cpuTempFallback = val;
                    }
                    else if (stype == "Clock" && name.Contains("Core") && !name.Contains("Effective") && !name.Contains("Average"))
                    {
                        if (!double.IsNaN(val) && val > 0)
                        {
                            cpuClockSum += val;
                            cpuClockCount++;
                        }
                    }
                }
            }
        }

        // Use fallbacks
        if (cpuTemp == 0 && cpuTempFallback > 0)
            cpuTemp = cpuTempFallback;

        if (gpuTemp == 0 && gpuEdgeTemp > 0)
            gpuTemp = gpuEdgeTemp;

        if (cpuClockCount > 0)
            cpuClock = cpuClockSum / cpuClockCount;

        return string.Format(
            "{{\"cpu_temp\":{0:F1},\"cpu_clock\":{1:F0},\"cpu_power\":{2:F1},\"gpu_temp\":{3:F1},\"gpu_percent\":{4:F1},\"gpu_clock\":{5:F0},\"gpu_memory_clock\":{6:F0},\"gpu_memory_percent\":{7:F1},\"gpu_power\":{8:F1}}}",
            cpuTemp, cpuClock, cpuPower, gpuTemp, gpuPercent, gpuClock, gpuMemClock, gpuMemPercent, gpuPower
        );
    }
}

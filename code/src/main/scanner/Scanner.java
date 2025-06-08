package com.scanner;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.regex.*;
import org.json.JSONObject;
import org.json.JSONArray;

public class Scanner {

    public static void main(String[] args) throws Exception {
        Set<String> scanned = new HashSet<>();
        List<ScanResult> allResults = new ArrayList<>();

        Path configFile = Paths.get("scanner", "jars_paths.txt");
        if (!Files.exists(configFile)) {
            System.out.println("No jars_paths.txt found in scanner folder.");
            return;
        }

        List<String> paths = Files.readAllLines(configFile);
        for (String line : paths) {
            Path folderPath = Paths.get(line.trim());
            if (!Files.exists(folderPath)) {
                System.out.println("Skipping non-existing path: " + line);
                continue;
            }
            try (DirectoryStream<Path> stream = Files.newDirectoryStream(folderPath, "*.jar")) {
                for (Path jar : stream) {
                    String lib = getJarLibraryName(jar);
                    String version = getJarVersion(jar);
                    if (lib != null && version != null) {
                        String uniqueKey = lib + "-" + version;
                        if (scanned.contains(uniqueKey)) continue;
                        scanned.add(uniqueKey);
                        ScanResult result = sendToAIEngine(lib, version, folderPath.toString());
                        if (result != null) {
                            allResults.add(result);
                        }
                    }
                }
            }
        }

        writeHtml(allResults);
    }

    private static String getJarLibraryName(Path jarPath) {
        String fileName = jarPath.getFileName().toString();
        Pattern pattern = Pattern.compile("([a-zA-Z0-9._-]+)-([0-9]+\\.[0-9]+.*)\\.jar");
        Matcher matcher = pattern.matcher(fileName);
        return matcher.find() ? matcher.group(1) : null;
    }

    private static String getJarVersion(Path jarPath) {
        String fileName = jarPath.getFileName().toString();
        Pattern pattern = Pattern.compile("([a-zA-Z0-9._-]+)-([0-9]+\\.[0-9]+.*)\\.jar");
        Matcher matcher = pattern.matcher(fileName);
        return matcher.find() ? matcher.group(2) : null;
    }

    private static ScanResult sendToAIEngine(String lib, String version, String folderPath) {
        try {
            URL url = new URL("http://localhost:8000/scan");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);

            JSONObject payload = new JSONObject();
            payload.put("library", lib);
            payload.put("version", version);

            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = payload.toString().getBytes("utf-8");
                os.write(input, 0, input.length);
            }

            BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "utf-8"));
            StringBuilder response = new StringBuilder();
            String responseLine;
            while ((responseLine = br.readLine()) != null) {
                response.append(responseLine.trim());
            }

            JSONObject json = new JSONObject(response.toString());
            return new ScanResult(lib, version, folderPath, json);

        } catch (Exception e) {
            System.out.println("Error scanning " + lib + ": " + e.getMessage());
            return null;
        }
    }

    private static void writeHtml(List<ScanResult> results) throws IOException {
        results.sort(Comparator.comparing(r -> r.lib + r.version));

        List<ScanResult> withCVEs = new ArrayList<>();
        for (ScanResult r : results) {
            if (r.hasCVEs()) withCVEs.add(r);
        }

        String timestamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
        String fileName = "scan_result_" + timestamp + ".html";

        Path outDir = Paths.get("out");
        Files.createDirectories(outDir);
        Path outFile = outDir.resolve(fileName);

        try (PrintWriter writer = new PrintWriter(Files.newBufferedWriter(outFile))) {
            writer.println("<html><head><title>Scan Results</title>");
            writer.println("<style>table{border-collapse:collapse;}td,th{border:1px solid #ccc;padding:6px;}</style>");
            writer.println("</head><body>");
            writer.println("<h2>JARs with CVEs Found</h2>");
            if (withCVEs.isEmpty()) {
                writer.println("<p>No CVEs found.</p>");
            } else {
                printTable(writer, withCVEs);
            }

            writer.println("<hr><h2>All Scanned JARs</h2>");
            printTable(writer, results);

            writer.println("<br><a href=\"http://localhost:8000/results\">Back to Results Home</a>");
            writer.println("</body></html>");
        }

        System.out.println("Results saved to: " + outFile.toAbsolutePath());
    }

    private static void printTable(PrintWriter writer, List<ScanResult> list) {
        writer.println("<table><tr><th>#</th><th>Library</th><th>Version</th><th>Folder</th><th>Risk Score</th><th>CVEs</th><th>Recommendation</th></tr>");
        int i = 1;
        for (ScanResult r : list) {
            writer.printf("<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td>%.2f</td><td>%s</td><td>%s</td></tr>%n",
                    i++, r.lib, r.version, r.folder, r.riskScore, r.cveSummary(), r.recommendation);
        }
        writer.println("</table>");
    }

    static class ScanResult {
        String lib, version, folder, recommendation;
        double riskScore;
        JSONArray cves;

        ScanResult(String lib, String version, String folder, JSONObject json) {
            this.lib = lib;
            this.version = version;
            this.folder = folder;
            this.riskScore = json.optDouble("risk_score", 0.0);
            this.recommendation = json.optString("recommendation", "N/A");
            this.cves = json.optJSONArray("cves") != null ? json.getJSONArray("cves") : new JSONArray();
        }

        boolean hasCVEs() {
            return cves.length() > 0;
        }

        String cveSummary() {
            if (cves.length() == 0) return "None";
            List<String> ids = new ArrayList<>();
            for (int i = 0; i < cves.length(); i++) {
                JSONObject cve = cves.getJSONObject(i);
                ids.add(cve.optString("id", "CVE-???"));
            }
            return String.join(", ", ids);
        }
    }
}

package main

import (
	"bufio"
	"compress/gzip"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	// parquet
	local "github.com/xitongsys/parquet-go-source/local"
	"github.com/xitongsys/parquet-go/parquet"
	pqreader "github.com/xitongsys/parquet-go/reader"
	pqwriter "github.com/xitongsys/parquet-go/writer"

	// avro
	"github.com/linkedin/goavro/v2"
)

type Metrics struct {
	Clicks      int64   `json:"clicks" parquet:"name=clicks, type=INT64"`
	Impressions int64   `json:"impressions" parquet:"name=impressions, type=INT64"`
	Revenue     float64 `json:"revenue" parquet:"name=revenue, type=DOUBLE"`
}

type Event struct {
	Date      string  `json:"date" parquet:"name=date, type=BYTE_ARRAY, convertedtype=UTF8"` // YYYY-MM-DD
	UserID    int64   `json:"user_id" parquet:"name=user_id, type=INT64"`
	EventType string  `json:"event_type" parquet:"name=event_type, type=BYTE_ARRAY, convertedtype=UTF8"`
	URL       string  `json:"url" parquet:"name=url, type=BYTE_ARRAY, convertedtype=UTF8"`
	UserAgent string  `json:"user_agent" parquet:"name=user_agent, type=BYTE_ARRAY, convertedtype=UTF8"`
	Value     float64 `json:"value" parquet:"name=value, type=DOUBLE"`
	Metrics   Metrics `json:"metrics" parquet:"name=metrics"`
}

// flags
var (
	mode         = flag.String("mode", "all", "mode: write|read|all")
	format       = flag.String("format", "all", "format to test: parquet|avro|json|all")
	outdir       = flag.String("outdir", "./out", "output directory for files")
	batches      = flag.Int("batches", 10, "number of batches to generate")
	rowsPerBatch = flag.Int("rows-per-batch", 200000, "rows per batch")
	parquetComp  = flag.String("parquet-comp", "SNAPPY", "Parquet compression: SNAPPY|GZIP|UNCOMPRESSED")
	avroCodec    = flag.String("avro-codec", "snappy", "Avro codec: snappy|deflate|null (informational, may not be applied)")
	jsonGzip     = flag.Bool("json-gzip", false, "gzip JSON output")
	filterDate   = flag.String("filter-date", "", "date to filter (YYYY-MM-DD)")
)

var eventTypes = []string{"click", "view", "purchase", "signup", "scroll", "hover"}

func main() {
	flag.Parse()
	rand.Seed(time.Now().UnixNano())
	runtime.GOMAXPROCS(runtime.NumCPU())

	if err := os.MkdirAll(*outdir, 0o755); err != nil {
		log.Fatal(err)
	}

	if *filterDate == "" {
		*filterDate = time.Now().AddDate(0, 0, -rand.Intn(365)).Format("2006-01-02")
	}

	fmt.Printf("Mode=%s format=%s outdir=%s batches=%d rows/batch=%d parquetComp=%s avroCodec=%s jsonGzip=%v filterDate=%s\n",
		*mode, *format, *outdir, *batches, *rowsPerBatch, *parquetComp, *avroCodec, *jsonGzip, *filterDate)

	if *mode == "write" || *mode == "all" {
		if err := writeSelected(); err != nil {
			log.Fatalf("write error: %v", err)
		}
	}

	if *mode == "read" || *mode == "all" {
		if err := readSelected(); err != nil {
			log.Fatalf("read error: %v", err)
		}
	}
}

func writeSelected() error {
	switch strings.ToLower(*format) {
	case "parquet":
		pf := filepath.Join(*outdir, "data.parquet")
		fmt.Println("=== Write: parquet ===")
		start := time.Now()
		if err := writeParquet(pf); err != nil {
			return err
		}
		fmt.Printf("Parquet written in %v\n", time.Since(start))
		showFileInfo(pf)
		return nil
	case "avro":
		af := filepath.Join(*outdir, "data.avro")
		fmt.Println("=== Write: avro ===")
		start := time.Now()
		if err := writeAvro(af); err != nil {
			return err
		}
		fmt.Printf("Avro written in %v\n", time.Since(start))
		showFileInfo(af)
		return nil
	case "json":
		jf := filepath.Join(*outdir, "data.ndjson")
		if *jsonGzip {
			jf += ".gz"
		}
		fmt.Println("=== Write: json ===")
		start := time.Now()
		if err := writeJSON(jf); err != nil {
			return err
		}
		fmt.Printf("JSON written in %v\n", time.Since(start))
		showFileInfo(jf)
		return nil
	case "all":
		if err := writeSelectedWithOrder([]string{"parquet", "avro", "json"}); err != nil {
			return err
		}
		return nil
	default:
		return fmt.Errorf("unknown format: %s", *format)
	}
}

func writeSelectedWithOrder(order []string) error {
	for _, f := range order {
		*format = f
		if err := writeSelected(); err != nil {
			return err
		}
	}
	return nil
}

func readSelected() error {
	switch strings.ToLower(*format) {
	case "parquet":
		pf := filepath.Join(*outdir, "data.parquet")
		fmt.Println("=== Read: parquet ===")
		start := time.Now()
		if err := readParquet(pf); err != nil {
			return err
		}
		fmt.Printf("Parquet read finished in %v\n", time.Since(start))
		return nil
	case "avro":
		af := filepath.Join(*outdir, "data.avro")
		fmt.Println("=== Read: avro ===")
		start := time.Now()
		if err := readAvro(af); err != nil {
			return err
		}
		fmt.Printf("Avro read finished in %v\n", time.Since(start))
		return nil
	case "json":
		jf := filepath.Join(*outdir, "data.ndjson")
		if *jsonGzip {
			jf += ".gz"
		}
		fmt.Println("=== Read: json ===")
		start := time.Now()
		if err := readJSON(jf); err != nil {
			return err
		}
		fmt.Printf("JSON read finished in %v\n", time.Since(start))
		return nil
	case "all":
		if err := readSelectedWithOrder([]string{"parquet", "avro", "json"}); err != nil {
			return err
		}
		return nil
	default:
		return fmt.Errorf("unknown format: %s", *format)
	}
}

func readSelectedWithOrder(order []string) error {
	for _, f := range order {
		*format = f
		if err := readSelected(); err != nil {
			return err
		}
	}
	return nil
}

func showFileInfo(path string) {
	fi, err := os.Stat(path)
	if err != nil {
		fmt.Printf("%s: (not found)\n", path)
		return
	}
	fmt.Printf("%s => %s (bytes=%d)\n", filepath.Base(path), fi.ModTime().Format(time.RFC3339), fi.Size())
}

func genBatch(n int) []Event {
	out := make([]Event, 0, n)
	baseDate := time.Now().AddDate(0, 0, -365)
	for i := 0; i < n; i++ {
		d := baseDate.AddDate(0, 0, rand.Intn(365)).Format("2006-01-02")
		e := Event{
			Date:      d,
			UserID:    int64(rand.Intn(10_000_000) + 1),
			EventType: eventTypes[rand.Intn(len(eventTypes))],
			URL:       fmt.Sprintf("https://example.com/page/%d", rand.Intn(10000)),
			UserAgent: fmt.Sprintf("GoBench/%d.%d", rand.Intn(3)+1, rand.Intn(10)),
			Value:     rand.Float64() * 100.0,
			Metrics: Metrics{
				Clicks:      int64(rand.Intn(10)),
				Impressions: int64(100 + rand.Intn(1000)),
				Revenue:     rand.Float64() * 10.0,
			},
		}
		out = append(out, e)
	}
	return out
}

/////////////////////////////////////////////////
// PARQUET
/////////////////////////////////////////////////

func writeParquet(path string) error {
	fw, err := local.NewLocalFileWriter(path)
	if err != nil {
		return err
	}
	defer fw.Close()

	pw, err := pqwriter.NewParquetWriter(fw, new(Event), 1)
	if err != nil {
		return err
	}
	defer func() {
		if err := pw.WriteStop(); err != nil {
			log.Printf("Parquet WriteStop error: %v", err)
		}
	}()

	switch strings.ToUpper(*parquetComp) {
	case "SNAPPY":
		pw.CompressionType = parquet.CompressionCodec_SNAPPY
	case "GZIP":
		pw.CompressionType = parquet.CompressionCodec_GZIP
	default:
		pw.CompressionType = parquet.CompressionCodec_UNCOMPRESSED
	}

	pw.RowGroupSize = 64 * 1024 * 1024
	pw.PageSize = 8 * 1024

	fmt.Printf("Writing Parquet to %s (comp=%s)\n", path, *parquetComp)

	total := 0
	for b := 0; b < *batches; b++ {
		batch := genBatch(*rowsPerBatch)
		for i := range batch {
			if err := pw.Write(batch[i]); err != nil {
				return fmt.Errorf("parquet write error: %w", err)
			}
			total++
		}
		batch = nil
	}
	fmt.Printf("Parquet: wrote %d rows\n", total)
	return nil
}

func readParquet(path string) error {
	// FULL SCAN
	fr, err := local.NewLocalFileReader(path)
	if err != nil {
		return err
	}
	pr, err := pqreader.NewParquetReader(fr, new(Event), 1)
	if err != nil {
		fr.Close()
		return err
	}
	num := int(pr.GetNumRows())
	fmt.Printf("Parquet reader: %d rows\n", num)

	start := time.Now()
	const chunk = 10000
	read := 0
	for read < num {
		toRead := chunk
		if num-read < chunk {
			toRead = num - read
		}
		rows := make([]Event, toRead)
		if err := pr.Read(&rows); err != nil {
			pr.ReadStop()
			fr.Close()
			return err
		}
		read += toRead
		rows = nil
	}
	fmt.Printf("Parquet full-scan time: %v\n", time.Since(start))
	pr.ReadStop()
	fr.Close()

	// FILTER
	fr, err = local.NewLocalFileReader(path)
	if err != nil {
		return err
	}
	pr, err = pqreader.NewParquetReader(fr, new(Event), 1)
	if err != nil {
		fr.Close()
		return err
	}
	start = time.Now()
	found := 0
	for i := 0; i < int(pr.GetNumRows()); {
		batch := 10000
		if int(pr.GetNumRows())-i < batch {
			batch = int(pr.GetNumRows()) - i
		}
		rows := make([]Event, batch)
		if err := pr.Read(&rows); err != nil {
			pr.ReadStop()
			fr.Close()
			return err
		}
		for _, r := range rows {
			if r.Date == *filterDate {
				found++
			}
		}
		i += batch
		rows = nil
	}
	fmt.Printf("Parquet filter(%s): found=%d time=%v\n", *filterDate, found, time.Since(start))
	pr.ReadStop()
	fr.Close()

	// AGGREGATION
	fr, err = local.NewLocalFileReader(path)
	if err != nil {
		return err
	}
	pr, err = pqreader.NewParquetReader(fr, new(Event), 1)
	if err != nil {
		fr.Close()
		return err
	}
	start = time.Now()
	counts := map[string]int64{}
	totalRows := 0
	for i := 0; i < int(pr.GetNumRows()); {
		batch := 10000
		if int(pr.GetNumRows())-i < batch {
			batch = int(pr.GetNumRows()) - i
		}
		rows := make([]Event, batch)
		if err := pr.Read(&rows); err != nil {
			pr.ReadStop()
			fr.Close()
			return err
		}
		for _, r := range rows {
			counts[r.EventType]++
			totalRows++
		}
		i += batch
		rows = nil
	}
	fmt.Printf("Parquet aggregation: rows=%d time=%v\n", totalRows, time.Since(start))
	fmt.Printf("Parquet counts sample: %v\n", sampleMap(counts, 5))
	pr.ReadStop()
	fr.Close()
	return nil
}

/////////////////////////////////////////////////
// AVRO
/////////////////////////////////////////////////

func avroSchema() string {
	return `{
  "type":"record",
  "name":"Event",
  "fields":[
    {"name":"date","type":"string"},
    {"name":"user_id","type":"long"},
    {"name":"event_type","type":"string"},
    {"name":"url","type":"string"},
    {"name":"user_agent","type":"string"},
    {"name":"value","type":"double"},
    {"name":"metrics", "type": {
        "type":"record", "name":"Metrics",
        "fields":[
          {"name":"clicks","type":"long"},
          {"name":"impressions","type":"long"},
          {"name":"revenue","type":"double"}
        ]
    }}
  ]
}`
}

func writeAvro(path string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	schema := avroSchema()
	codec, err := goavro.NewCodec(schema)
	if err != nil {
		return err
	}

	cfg := goavro.OCFConfig{
		W:     f,
		Codec: codec,
	}
	ocfWriter, err := goavro.NewOCFWriter(cfg)
	if err != nil {
		return err
	}

	fmt.Printf("Writing Avro OCF to %s (codec flag=%s)\n", path, *avroCodec)
	total := 0
	for b := 0; b < *batches; b++ {
		batch := genBatch(*rowsPerBatch)
		records := make([]interface{}, 0, len(batch))
		for _, e := range batch {
			rec := map[string]interface{}{
				"date":       e.Date,
				"user_id":    e.UserID,
				"event_type": e.EventType,
				"url":        e.URL,
				"user_agent": e.UserAgent,
				"value":      e.Value,
				"metrics": map[string]interface{}{
					"clicks":      e.Metrics.Clicks,
					"impressions": e.Metrics.Impressions,
					"revenue":     e.Metrics.Revenue,
				},
			}
			records = append(records, rec)
		}
		if err := ocfWriter.Append(records); err != nil {
			return err
		}
		total += len(records)
		records = nil
		batch = nil
	}
	fmt.Printf("Avro: wrote %d rows\n", total)
	return nil
}

func readAvro(path string) error {
	// FULL SCAN
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	ocfr, err := goavro.NewOCFReader(f)
	if err != nil {
		return err
	}
	fmt.Printf("Avro OCF reader compression=%s\n", ocfr.CompressionName())

	start := time.Now()
	total := 0
	for ocfr.Scan() {
		if _, err := ocfr.Read(); err != nil {
			return err
		}
		total++
	}
	fmt.Printf("Avro full-scan rows read (approx)=%d time=%v\n", total, time.Since(start))

	// FILTER
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}
	ocfr, err = goavro.NewOCFReader(f)
	if err != nil {
		return err
	}
	start = time.Now()
	found := 0
	for ocfr.Scan() {
		datum, err := ocfr.Read()
		if err != nil {
			return err
		}
		m := datum.(map[string]interface{})
		if m["date"].(string) == *filterDate {
			found++
		}
	}
	fmt.Printf("Avro filter(%s): found=%d time=%v\n", *filterDate, found, time.Since(start))

	// AGGREGATION
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}
	ocfr, err = goavro.NewOCFReader(f)
	if err != nil {
		return err
	}
	start = time.Now()
	counts := map[string]int64{}
	totalRows := 0
	for ocfr.Scan() {
		datum, err := ocfr.Read()
		if err != nil {
			return err
		}
		m := datum.(map[string]interface{})
		ev := m["event_type"].(string)
		counts[ev]++
		totalRows++
	}
	fmt.Printf("Avro aggregation: rows=%d time=%v\n", totalRows, time.Since(start))
	fmt.Printf("Avro counts sample: %v\n", sampleMap(counts, 5))
	return nil
}

/////////////////////////////////////////////////
// JSON
/////////////////////////////////////////////////

func writeJSON(path string) error {
	fmt.Printf("Writing JSON NDJSON to %s (gzip=%v)\n", path, *jsonGzip)
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	var w *bufio.Writer
	var gz *gzip.Writer
	if *jsonGzip {
		gz = gzip.NewWriter(f)
		defer gz.Close()
		w = bufio.NewWriter(gz)
	} else {
		w = bufio.NewWriter(f)
	}
	enc := json.NewEncoder(w)
	total := 0
	for b := 0; b < *batches; b++ {
		batch := genBatch(*rowsPerBatch)
		for _, e := range batch {
			if err := enc.Encode(e); err != nil {
				return err
			}
			total++
		}
		batch = nil
	}
	w.Flush()
	fmt.Printf("JSON: wrote %d rows\n", total)
	return nil
}

func readJSON(path string) error {
	// FULL-SCAN
	fmt.Printf("Reading JSON from %s\n", path)
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	var r io.Reader
	if *jsonGzip || strings.HasSuffix(path, ".gz") {
		gz, err := gzip.NewReader(f)
		if err != nil {
			return err
		}
		defer gz.Close()
		r = gz
	} else {
		r = f
	}

	dec := json.NewDecoder(r)

	start := time.Now()
	rows := 0
	for {
		var e Event
		if err := dec.Decode(&e); err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
		rows++
	}
	fmt.Printf("JSON full-scan rows=%d time=%v\n", rows, time.Since(start))

	// FILTER
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}
	if *jsonGzip || strings.HasSuffix(path, ".gz") {
		gz, err := gzip.NewReader(f)
		if err != nil {
			return err
		}
		defer gz.Close()
		dec = json.NewDecoder(gz)
	} else {
		dec = json.NewDecoder(f)
	}

	start = time.Now()
	found := 0
	for {
		var e Event
		if err := dec.Decode(&e); err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
		if e.Date == *filterDate {
			found++
		}
	}
	fmt.Printf("JSON filter(%s): found=%d time=%v\n", *filterDate, found, time.Since(start))

	// AGGREGATION
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}
	if *jsonGzip || strings.HasSuffix(path, ".gz") {
		gz, err := gzip.NewReader(f)
		if err != nil {
			return err
		}
		defer gz.Close()
		dec = json.NewDecoder(gz)
	} else {
		dec = json.NewDecoder(f)
	}
	start = time.Now()
	counts := map[string]int64{}
	totalRows := 0
	for {
		var e Event
		if err := dec.Decode(&e); err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
		counts[e.EventType]++
		totalRows++
	}
	fmt.Printf("JSON aggregation: rows=%d time=%v\n", totalRows, time.Since(start))
	fmt.Printf("JSON counts sample: %v\n", sampleMap(counts, 5))
	return nil
}

func sampleMap(m map[string]int64, n int) string {
	parts := []string{}
	i := 0
	for k, v := range m {
		parts = append(parts, fmt.Sprintf("%s=%d", k, v))
		i++
		if i >= n {
			break
		}
	}
	return strings.Join(parts, ", ")
}

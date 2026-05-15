package main

import (
	"bytes"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"text/template"

	"gopkg.in/yaml.v3"
)

type workflowConfig struct {
	WorkflowName       string `yaml:"workflowName"`
	Namespace          string `yaml:"namespace"`
	Environment        string `yaml:"environment"`
	Schedule           string `yaml:"schedule"`
	Suspend            bool   `yaml:"suspend"`
	SparkImage         string `yaml:"sparkImage"`
	SparkMainFile      string `yaml:"sparkMainFile"`
	InputPath          string `yaml:"inputPath"`
	OutputPath         string `yaml:"outputPath"`
	DriverCores        int    `yaml:"driverCores"`
	DriverMemory       string `yaml:"driverMemory"`
	ExecutorCores      int    `yaml:"executorCores"`
	ExecutorInstances  int    `yaml:"executorInstances"`
	ExecutorMemory     string `yaml:"executorMemory"`
	ServiceAccountName string `yaml:"serviceAccountName"`
	ReportTitle        string `yaml:"reportTitle"`
}

func main() {
	configPath := flag.String("config", "", "Путь к файлу с параметрами YAML")
	templatePath := flag.String("template", "", "Путь к шаблону workflow")
	outputPath := flag.String("output", "", "Куда записать сгенерированный YAML")
	flag.Parse()

	if *configPath == "" || *templatePath == "" || *outputPath == "" {
		fail("нужно передать -config, -template и -output")
	}

	cfg := readConfig(*configPath)
	rendered := renderTemplate(*templatePath, cfg)

	if err := os.MkdirAll(filepath.Dir(*outputPath), 0o755); err != nil {
		fail("не удалось создать каталог для результата: %v", err)
	}

	if err := os.WriteFile(*outputPath, rendered, 0o644); err != nil {
		fail("не удалось записать результат: %v", err)
	}

	fmt.Printf("Сгенерирован workflow: %s\n", *outputPath)
}

func readConfig(path string) workflowConfig {
	raw, err := os.ReadFile(path)
	if err != nil {
		fail("не удалось прочитать конфигурацию %s: %v", path, err)
	}

	var cfg workflowConfig
	if err := yaml.Unmarshal(raw, &cfg); err != nil {
		fail("не удалось разобрать YAML %s: %v", path, err)
	}

	if cfg.WorkflowName == "" {
		fail("в конфигурации не задан workflowName")
	}
	if cfg.Namespace == "" {
		cfg.Namespace = "argo"
	}
	if cfg.SparkMainFile == "" {
		cfg.SparkMainFile = "local:///opt/spark/app/job.py"
	}
	if cfg.ServiceAccountName == "" {
		cfg.ServiceAccountName = "spark-driver"
	}
	if cfg.ReportTitle == "" {
		cfg.ReportTitle = "Отчёт о запуске Spark-задачи"
	}

	return cfg
}

func renderTemplate(path string, cfg workflowConfig) []byte {
	raw, err := os.ReadFile(path)
	if err != nil {
		fail("не удалось прочитать шаблон %s: %v", path, err)
	}

	tpl, err := template.New(filepath.Base(path)).
		Delims("[[", "]]").
		Option("missingkey=error").
		Parse(string(raw))
	if err != nil {
		fail("не удалось разобрать шаблон %s: %v", path, err)
	}

	var buf bytes.Buffer
	if err := tpl.Execute(&buf, cfg); err != nil {
		fail("не удалось подставить значения в шаблон: %v", err)
	}

	return buf.Bytes()
}

func fail(format string, args ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
	os.Exit(1)
}

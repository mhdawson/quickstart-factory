{{- define "nightly-ci-fixture.fullname" -}}
{{- .Release.Name -}}
{{- end -}}

{{- define "nightly-ci-fixture.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "nightly-ci-fixture.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "stt.labels" -}}
app.kubernetes.io/name: stt
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels for server
*/}}
{{- define "stt.serverLabels" -}}
app.kubernetes.io/name: stt
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: server
{{- end -}}

{{/*
Selector labels for worker
*/}}
{{- define "stt.workerLabels" -}}
app.kubernetes.io/name: stt
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: worker
{{- end -}}

{{/*
Full name
*/}}
{{- define "stt.fullname" -}}
{{ .Release.Name }}-stt
{{- end -}}

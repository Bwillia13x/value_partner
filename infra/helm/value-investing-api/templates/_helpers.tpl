{{/* Generate app name */}}
{{- define "value-investing-api.name" -}}
value-investing-api
{{- end }}

{{- define "value-investing-api.fullname" -}}
{{ include "value-investing-api.name" . }}
{{- end }}
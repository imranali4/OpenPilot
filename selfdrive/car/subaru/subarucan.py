from cereal import car

VisualAlert = car.CarControl.HUDControl.VisualAlert

INFOTAINMENT_STATUS_SIGNALS = [
  "LKAS_State_Infotainment",
  "LKAS_Blue_Lines",
  "Signal1",
  "Signal2",
]

ES_DISTANCE_SIGNALS = [
  "COUNTER",
  "Signal1",
  "Cruise_Fault",
  "Cruise_Throttle",
  "Signal2",
  "Car_Follow",
  "Signal3",
  "Cruise_Soft_Disable",
  "Signal7",
  "Cruise_Brake_Active",
  "Distance_Swap",
  "Cruise_EPB",
  "Signal4",
  "Close_Distance",
  "Signal5",
  "Cruise_Cancel",
  "Cruise_Set",
  "Cruise_Resume",
  "Signal6",
]

ES_LKAS_STATE_SIGNALS = [
  "COUNTER",
  "LKAS_Alert_Msg",
  "Signal1",
  "LKAS_ACTIVE",
  "LKAS_Dash_State",
  "Signal2",
  "Backward_Speed_Limit_Menu",
  "LKAS_Left_Line_Enable",
  "LKAS_Left_Line_Light_Blink",
  "LKAS_Right_Line_Enable",
  "LKAS_Right_Line_Light_Blink",
  "LKAS_Left_Line_Visible",
  "LKAS_Right_Line_Visible",
  "LKAS_Alert",
  "Signal3",
]

ES_DASHSTATUS_SIGNALS = [
  "COUNTER",
  "PCB_Off",
  "LDW_Off",
  "Signal1",
  "Cruise_State_Msg",
  "LKAS_State_Msg",
  "Signal2",
  "Cruise_Soft_Disable",
  "EyeSight_Status_Msg",
  "Signal3",
  "Cruise_Distance",
  "Signal4",
  "Conventional_Cruise",
  "Signal5",
  "Cruise_Disengaged",
  "Cruise_Activated",
  "Signal6",
  "Cruise_Set_Speed",
  "Cruise_Fault",
  "Cruise_On",
  "Display_Own_Car",
  "Brake_Lights",
  "Car_Follow",
  "Signal7",
  "Far_Distance",
  "Cruise_State",
]


def create_steering_control(packer, apply_steer):
  values = {
    "LKAS_Output": apply_steer,
    "LKAS_Request": 1 if apply_steer != 0 else 0,
    "SET_1": 1
  }
  return packer.make_can_msg("ES_LKAS", 0, values)

def create_steering_status(packer):
  return packer.make_can_msg("ES_LKAS_State", 0, {})

def create_es_distance(packer, es_distance_msg, bus, pcm_cancel_cmd):
  values = {k: es_distance_msg[k] for k in ES_DISTANCE_SIGNALS}
  values["COUNTER"] = (values["COUNTER"] + 1) % 0x10
  if pcm_cancel_cmd:
    values["Cruise_Cancel"] = 1
  return packer.make_can_msg("ES_Distance", bus, values)

def create_es_lkas_state(packer, es_lkas_state_msg, enabled, visual_alert, left_line, right_line, left_lane_depart, right_lane_depart):

  values = {k: es_lkas_state_msg[k] for k in ES_DASHSTATUS_SIGNALS}

  # Filter the stock LKAS "Keep hands on wheel" alert
  if values["LKAS_Alert_Msg"] == 1:
    values["LKAS_Alert_Msg"] = 0

  # Filter the stock LKAS sending an audible alert when it turns off LKAS
  if values["LKAS_Alert"] == 27:
    values["LKAS_Alert"] = 0

  # Filter the stock LKAS sending an audible alert when "Keep hands on wheel" alert is active (2020+ models)
  if values["LKAS_Alert"] == 28 and values["LKAS_Alert_Msg"] == 7:
    values["LKAS_Alert"] = 0

  # Filter the stock LKAS sending an audible alert when "Keep hands on wheel OFF" alert is active (2020+ models)
  if values["LKAS_Alert"] == 30:
    values["LKAS_Alert"] = 0

  # Filter the stock LKAS sending "Keep hands on wheel OFF" alert (2020+ models)
  if values["LKAS_Alert_Msg"] == 7:
    values["LKAS_Alert_Msg"] = 0

  # Show Keep hands on wheel alert for openpilot steerRequired alert
  if visual_alert == VisualAlert.steerRequired:
    values["LKAS_Alert_Msg"] = 1

  # Ensure we don't overwrite potentially more important alerts from stock (e.g. FCW)
  if visual_alert == VisualAlert.ldw and values["LKAS_Alert"] == 0:
    if left_lane_depart:
      values["LKAS_Alert"] = 12 # Left lane departure dash alert
    elif right_lane_depart:
      values["LKAS_Alert"] = 11 # Right lane departure dash alert

  values["LKAS_ACTIVE"] = 1 # Show LKAS lane lines
  values["LKAS_Dash_State"] = 2 if enabled else 0 # Green enabled indicator

  values["LKAS_Left_Line_Visible"] = int(left_line)
  values["LKAS_Right_Line_Visible"] = int(right_line)

  return packer.make_can_msg("ES_LKAS_State", 0, values)

def create_es_dashstatus(packer, dashstatus_msg):
  values = {k: dashstatus_msg[k] for k in ES_DASHSTATUS_SIGNALS}

  # Filter stock LKAS disabled and Keep hands on steering wheel OFF alerts
  if values["LKAS_State_Msg"] in (2, 3):
    values["LKAS_State_Msg"] = 0

  return packer.make_can_msg("ES_DashStatus", 0, values)

def create_infotainmentstatus(packer, infotainmentstatus_msg, visual_alert):
  # Filter stock LKAS disabled and Keep hands on steering wheel OFF alerts
  values = {k: infotainmentstatus_msg[k] for k in INFOTAINMENT_STATUS_SIGNALS}
  if values["LKAS_State_Infotainment"] in (3, 4):
    values["LKAS_State_Infotainment"] = 0

  # Show Keep hands on wheel alert for openpilot steerRequired alert
  if visual_alert == VisualAlert.steerRequired:
    values["LKAS_State_Infotainment"] = 3

  # Show Obstacle Detected for fcw
  if visual_alert == VisualAlert.fcw:
    values["LKAS_State_Infotainment"] = 2

  return packer.make_can_msg("INFOTAINMENT_STATUS", 0, values)

# *** Subaru Pre-global ***

def subaru_preglobal_checksum(packer, values, addr):
  dat = packer.make_can_msg(addr, 0, values)[2]
  return (sum(dat[:7])) % 256

def create_preglobal_steering_control(packer, apply_steer):
  values = {
    "LKAS_Command": apply_steer,
    "LKAS_Active": 1 if apply_steer != 0 else 0
  }
  values["Checksum"] = subaru_preglobal_checksum(packer, values, "ES_LKAS")

  return packer.make_can_msg("ES_LKAS", 0, values)

def create_preglobal_es_distance(packer, cruise_button, es_distance_msg):

  values = {k: es_distance_msg[k] for k in ES_DISTANCE_SIGNALS}
  values["Cruise_Button"] = cruise_button

  values["Checksum"] = subaru_preglobal_checksum(packer, values, "ES_Distance")

  return packer.make_can_msg("ES_Distance", 0, values)
